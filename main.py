"""Bot de Ofertas Shopee — busca, filtra, gera link de afiliado, posta e atualiza o site.

Uso:
  python main.py            -> execução real (precisa do .env preenchido)
  python main.py --teste    -> modo simulado com produtos de exemplo (não posta nada)
"""
import argparse
import json
import os
import random
import time
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from site_generator import gerar_site
from telegram_poster import TelegramPoster, montar_mensagem

BASE = Path(__file__).parent
DATA = BASE / "data"
POSTADOS = DATA / "postados.json"     # itemId -> data do post (evita repetir)
OFERTAS = DATA / "ofertas.json"       # vitrine do site
WHATS = DATA / "whatsapp_hoje.txt"    # textos prontos p/ colar no WhatsApp
FILA = DATA / "fila.csv"              # modo manual: produtos que você cadastrou
BRT = timezone(timedelta(hours=-3))


def cfg(nome, padrao=None):
    v = os.getenv(nome)
    return v if v not in (None, "") else padrao


def carregar(path, padrao):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return padrao


def salvar(path, dados):
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def normalizar(p: dict) -> dict:
    preco = float(p.get("priceMin") or 0)
    desconto = int(p.get("priceDiscountRate") or 0)
    original = round(preco / (1 - desconto / 100), 2) if 0 < desconto < 100 else None
    return {
        "id": str(p.get("itemId") or p.get("productLink") or p.get("productName")),
        "nome": p.get("productName", "").strip(),
        "preco": preco,
        "preco_original": original,
        "desconto": desconto,
        "imagem": p.get("imageUrl"),
        "nota": float(p.get("ratingStar") or 0),
        "vendas": int(p.get("sales") or 0),
        "comissao": float(p.get("commissionRate") or 0),
        "loja": p.get("shopName"),
        "link": p.get("offerLink") or p.get("productLink"),
        "produto_url": p.get("productLink"),
    }


import unicodedata


def _sem_acento(t):
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def combina_com_busca(nome, keyword):
    """O produto só entra se o nome tiver todas as palavras da busca (ex.: 'mouse gamer')."""
    nome = _sem_acento(nome)
    return all(w in nome for w in _sem_acento(keyword).split() if len(w) > 2)


def passa_filtro(o, min_desc, min_nota, min_vendas, preco_max, campos=None):
    """Só aplica o filtro de um campo se a API devolveu esse campo."""
    tem = lambda c: campos is None or c in campos
    return ((not tem("priceDiscountRate") or o["desconto"] >= min_desc)
            and (not tem("ratingStar") or o["nota"] >= min_nota)
            and (not tem("sales") or o["vendas"] >= min_vendas)
            and o["preco"] > 0 and (preco_max <= 0 or o["preco"] <= preco_max) and o["link"])


def produtos_exemplo(keyword):
    random.seed(keyword)
    itens = []
    for i in range(6):
        itens.append({
            "itemId": zlib.crc32((keyword + str(i)).encode()),
            "productName": f"{keyword.title()} modelo exemplo {i + 1}",
            "priceMin": str(round(random.uniform(29, 399), 2)),
            "priceDiscountRate": random.choice([0, 10, 25, 35, 50]),
            "imageUrl": f"https://placehold.co/400x400/ee4d2d/ffffff?text={keyword.split()[0]}",
            "ratingStar": str(round(random.uniform(4.0, 5.0), 1)),
            "sales": random.randint(10, 5000),
            "commissionRate": "0.08",
            "shopName": "Loja Exemplo",
            "productLink": "https://shopee.com.br/",
            "offerLink": "https://s.shopee.com.br/exemplo",
        })
    return itens


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--teste", action="store_true", help="modo simulado, sem postar")
    ap.add_argument("--manual", action="store_true", help="com --teste: simula o modo planilha")
    ap.add_argument("--previa", action="store_true", help="usa a API de verdade, mas NÃO posta nem salva nada")
    args = ap.parse_args()
    load_dotenv(BASE / "configuracao.txt", encoding="utf-8-sig")
    load_dotenv(BASE / ".env")

    keywords = [k.strip() for k in cfg("KEYWORDS", "fone bluetooth,mouse gamer").split(",") if k.strip()]
    por_execucao = int(cfg("POSTS_PER_RUN", 3))
    min_desc = int(cfg("MIN_DISCOUNT", 20))
    min_nota = float(cfg("MIN_RATING", 4.5))
    min_vendas = int(cfg("MIN_SALES", 50))
    preco_max = float(cfg("MAX_PRICE", 0))
    sort_type = int(cfg("SORT_TYPE", 2))
    dias_sem_repetir = int(cfg("DAYS_NO_REPEAT", 7))
    busca_exata = cfg("STRICT_KEYWORDS", "1") != "0"
    site_titulo = cfg("SITE_TITLE", "Tech Barato BR")
    canal_link = cfg("TELEGRAM_CHANNEL_LINK", "")

    # Sem App ID da Shopee -> MODO MANUAL (posta o que você colocou em data/fila.csv)
    manual = not cfg("SHOPEE_APP_ID") and (not args.teste or args.manual)
    api = None
    if not args.teste and not manual:
        from shopee_api import ShopeeAffiliate
        api = ShopeeAffiliate(cfg("SHOPEE_APP_ID"), cfg("SHOPEE_APP_SECRET"))
    print("Modo:", "MANUAL (planilha data/fila.csv)" if manual else ("TESTE" if args.teste else "AUTOMÁTICO (API)"))

    postados = carregar(POSTADOS, {})
    limite = datetime.now(BRT) - timedelta(days=dias_sem_repetir)
    postados = {k: v for k, v in postados.items() if datetime.fromisoformat(v) > limite}

    candidatos = []
    fila_restante = None
    if manual:
        from fila_manual import ler_fila
        fila = ler_fila(BASE / "fila_exemplo.csv" if args.teste else FILA)
        candidatos, fila_restante = fila[:por_execucao], fila[por_execucao:]
        keywords = []
    for kw in keywords:
        try:
            brutos = produtos_exemplo(kw) if args.teste else api.buscar_produtos(kw, sort_type=sort_type, limit=30)
        except Exception as e:
            print(f"[aviso] falha buscando '{kw}': {e}")
            continue
        for p in brutos:
            o = normalizar(p)
            o["categoria"] = kw
            if o["id"] not in postados and (not busca_exata or combina_com_busca(o["nome"], kw)) and passa_filtro(o, min_desc, min_nota, min_vendas, preco_max, getattr(api, "_campos", None)):
                candidatos.append(o)
        time.sleep(0 if args.teste else 1)

    # prioriza: maior desconto, depois mais vendas; evita repetir a mesma categoria em sequência
    candidatos.sort(key=lambda o: (o["desconto"], o["vendas"]), reverse=True)
    escolhidos, cats = [], set()
    for o in candidatos:
        if len(escolhidos) >= por_execucao:
            break
        if o["categoria"] in cats and len(cats) < len(keywords):
            continue
        escolhidos.append(o); cats.add(o["categoria"])
    for o in candidatos:
        if len(escolhidos) >= por_execucao:
            break
        if o not in escolhidos:
            escolhidos.append(o)

    print(f"{len(candidatos)} ofertas passaram no filtro; postando {len(escolhidos)}.")

    poster = None
    if not args.teste and not args.previa and cfg("TELEGRAM_BOT_TOKEN") and cfg("TELEGRAM_CHAT_ID"):
        poster = TelegramPoster(cfg("TELEGRAM_BOT_TOKEN"), cfg("TELEGRAM_CHAT_ID"))

    agora = datetime.now(BRT)
    vitrine = carregar(OFERTAS, [])
    textos_whats = []
    falhou = []
    enviados = []
    for o in escolhidos:
        # link curto rastreável (subId = categoria, para ver no relatório o que vende)
        if api and o.get("produto_url"):
            try:
                o["link"] = api.link_curto(o["produto_url"], sub_id=o["categoria"].replace(" ", "")[:50])
            except Exception as e:
                print(f"[aviso] link curto falhou, usando offerLink: {e}")
        if poster:
            try:
                poster.postar(o)
            except Exception as e:
                print(f"[erro] Telegram: {e}")
                falhou.append(o)
                continue
            time.sleep(3)
        else:
            print("\n--- PRÉVIA ---\n" + montar_mensagem(o))
        postados[o["id"]] = agora.isoformat()
        o["postado_em"] = agora.isoformat()
        o.pop("_linha", None)
        enviados.append(o)
        vitrine = [v for v in vitrine if v["id"] != o["id"]]
        vitrine.insert(0, o)
        textos_whats.append(montar_mensagem(o).replace("<b>", "*").replace("</b>", "*")
                            .replace("<s>", "~").replace("</s>", "~").replace("<i>", "_").replace("</i>", "_")
                            .replace(f"<a href=\"{o['link']}\">COMPRAR NA SHOPEE</a>", o["link"]))

    # Instagram: gera a arte do story das melhores ofertas e põe na fila
    ig_qtd = int(cfg("IG_STORIES_PER_RUN", 1))
    if (cfg("IG_ACCESS_TOKEN") or args.teste) and not args.previa and enviados and ig_qtd > 0:
        from stories_ig import enfileirar, limpar_antigos
        limpar_antigos()
        melhores = sorted(enviados, key=lambda o: (o["desconto"], o["vendas"]), reverse=True)
        enfileirar(melhores, cfg("TELEGRAM_CHAT_ID", "@techbarato_ofertas"),
                   cfg("IG_HANDLE", "@techbarato.ofertas"), ig_qtd)

    if manual and not args.teste and not args.previa:
        from fila_manual import salvar_fila
        salvar_fila(FILA, falhou + fila_restante)  # tira da fila o que foi postado
        print(f"Restam {len(falhou) + len(fila_restante)} produtos na fila.")

    if args.previa:
        print("\n[PRÉVIA] Nada foi postado nem salvo.")
        return
    vitrine = vitrine[:int(cfg("SITE_MAX_ITEMS", 60))]
    salvar(POSTADOS, postados)
    salvar(OFERTAS, vitrine)
    if textos_whats:
        with WHATS.open("a", encoding="utf-8") as f:
            for t in textos_whats:
                f.write(t + "\n\n" + "=" * 30 + "\n\n")
    gerar_site(vitrine, BASE / "docs" / "index.html", site_titulo, canal_link)
    print("Site atualizado em docs/index.html")


if __name__ == "__main__":
    main()
