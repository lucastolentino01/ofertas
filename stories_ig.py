"""Gera a arte do story (1080x1920, JPEG) de cada oferta e coloca na fila de publicação.

As imagens ficam em docs/stories/ (o Instagram exige que a imagem esteja num
link público) e a fila em data/stories_pendentes.json. Quem publica é o
publicar_stories.py, que roda logo depois no GitHub.
"""
import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

BASE = Path(__file__).parent
FONTES = BASE / "fontes"
PASTA = BASE / "docs" / "stories"
FILA = BASE / "data" / "stories_pendentes.json"
BRT = timezone(timedelta(hours=-3))

W, H = 1080, 1920
PRETO, LARANJA, BRANCO, CINZA = (18, 18, 20), (255, 106, 43), (255, 255, 255), (160, 160, 168)


def _f(nome, tam):
    try:
        return ImageFont.truetype(str(FONTES / nome), tam)
    except OSError:
        return ImageFont.load_default(tam)


BLACK = lambda t: _f("InterDisplay-Black.otf", t)
BOLD = lambda t: _f("Inter-Bold.otf", t)
MED = lambda t: _f("Inter-Medium.otf", t)


def _brl(v):
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fundo():
    img = Image.new("RGB", (W, H), PRETO)
    brilho = Image.new("L", (W, H), 0)
    ImageDraw.Draw(brilho).ellipse((W - 700, -400, W + 500, 800), fill=60)
    img.paste(Image.new("RGB", (W, H), (50, 50, 56)), mask=brilho.filter(ImageFilter.GaussianBlur(220)))
    return img


def _foto(url):
    if not url:
        return None
    try:
        r = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception as e:
        print(f"   [aviso] foto não baixou: {e}")
        return None


def _quebrar(d, texto, fonte, largura, max_linhas):
    linhas, atual = [], ""
    for p in texto.split():
        teste = (atual + " " + p).strip()
        if d.textlength(teste, font=fonte) <= largura:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    if len(linhas) > max_linhas:
        linhas = linhas[:max_linhas]
        while d.textlength(linhas[-1] + "…", font=fonte) > largura and len(linhas[-1]) > 1:
            linhas[-1] = linhas[-1][:-1]
        linhas[-1] = linhas[-1].rstrip() + "…"
    return linhas


def _nome_curto(nome):
    """Nomes da Shopee são enormes: fica com o começo, sem repetições."""
    corte = nome.split(" - ")[0].split(" | ")[0]
    palavras = corte.split()[:7]
    while palavras and palavras[-1].lower() in {"de", "do", "da", "com", "para", "e", "sem", "p/", "-", "|", "em"}:
        palavras.pop()
    return " ".join(palavras)


def desenhar(o, canal="@techbarato_ofertas", arroba="@techbarato.ofertas", foto=None):
    img = _fundo()
    d = ImageDraw.Draw(img)

    # topo
    f = BOLD(32)
    d.rounded_rectangle((90, 220, 90 + d.textlength("ACHADINHO DO DIA", font=f) + 48, 288), radius=12, fill=LARANJA)
    d.text((114, 254), "ACHADINHO DO DIA", font=f, fill=PRETO, anchor="lm")
    d.text((W - 90, 254), "TECH BARATO", font=BLACK(40), fill=BRANCO, anchor="rm")

    # foto
    x0, y0, x1, y1 = 90, 330, W - 90, 330 + 680
    d.rounded_rectangle((x0, y0, x1, y1), radius=44, fill=BRANCO)
    foto = foto if foto is not None else _foto(o.get("imagem"))
    if foto:
        foto = ImageOps.contain(foto, (x1 - x0 - 60, y1 - y0 - 60))
        img.paste(foto, (x0 + (x1 - x0 - foto.width) // 2, y0 + (y1 - y0 - foto.height) // 2))

    # selo % OFF
    if o.get("desconto"):
        r, cx, cy = 115, x1 - 135, y0 + 135
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=LARANJA)
        d.text((cx, cy - 20), f"{o['desconto']}%", font=BLACK(80), fill=PRETO, anchor="mm")
        d.text((cx, cy + 46), "OFF", font=BLACK(40), fill=PRETO, anchor="mm")

    # nota e vendas sobre a foto
    meta = []
    if o.get("nota"):
        meta.append(f"Nota {o['nota']:.1f}".replace(".", ","))
    if o.get("vendas"):
        meta.append(f"{o['vendas']:,} vendidos".replace(",", "."))
    if meta:
        t = " · ".join(meta)
        fm = BOLD(30)
        w = d.textlength(t, font=fm)
        d.rounded_rectangle((x0 + 30, y1 - 90, x0 + 30 + w + 40, y1 - 30), radius=12, fill=(18, 18, 20), outline=LARANJA, width=3)
        d.text((x0 + 50, y1 - 60), t, font=fm, fill=BRANCO, anchor="lm")

    # nome
    y = y1 + 46
    for linha in _quebrar(d, _nome_curto(o["nome"]), BOLD(52), W - 180, 2):
        d.text((90, y), linha, font=BOLD(52), fill=BRANCO)
        y += 64

    # preço
    y += 22
    if o.get("preco_original") and o["preco_original"] > o["preco"]:
        de = f"De R$ {_brl(o['preco_original'])}"
        d.text((90, y), de, font=MED(40), fill=CINZA)
        xa = 90 + d.textlength("De ", font=MED(40))
        d.line((xa, y + 26, 90 + d.textlength(de, font=MED(40)), y + 26), fill=CINZA, width=4)
        d.text((90 + d.textlength(de, font=MED(40)) + 14, y), "por", font=MED(40), fill=CINZA)
        y += 56
    inteiro, cent = _brl(o["preco"]).split(",")
    base = y + 170
    d.text((90, base - 95), "R$", font=BLACK(64), fill=LARANJA, anchor="ls")
    xi = 90 + d.textlength("R$", font=BLACK(64)) + 14
    d.text((xi, base), inteiro, font=BLACK(200), fill=LARANJA, anchor="ls")
    d.text((xi + d.textlength(inteiro, font=BLACK(200)) + 4, base - 92), "," + cent, font=BLACK(96), fill=LARANJA, anchor="ls")

    # chamada (o story automático não tem adesivo de link)
    cy0 = H - 470
    d.rounded_rectangle((90, cy0, W - 90, cy0 + 170), radius=28, fill=LARANJA)
    d.text((W // 2, cy0 + 58), "LINK NO TELEGRAM", font=BLACK(54), fill=PRETO, anchor="mm")
    d.text((W // 2, cy0 + 120), f"toque na bio  →  {canal}", font=BOLD(34), fill=PRETO, anchor="mm")

    d.text((W // 2, H - 262), "preço pode mudar a qualquer momento", font=MED(26), fill=CINZA, anchor="mm")
    d.text((W // 2, H - 214), arroba, font=BOLD(34), fill=BRANCO, anchor="mm")
    return img


def _carregar_fila():
    try:
        return json.loads(FILA.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def enfileirar(ofertas, canal, arroba, quantidade=1):
    """Gera as artes das melhores ofertas e coloca na fila."""
    PASTA.mkdir(parents=True, exist_ok=True)
    fila = _carregar_fila()
    ja = {i["id"] for i in fila}
    feitos = 0
    for o in ofertas:
        if feitos >= quantidade:
            break
        if o["id"] in ja:
            continue
        nome = f"{o['id']}.jpg"
        try:
            desenhar(o, canal, arroba).save(PASTA / nome, "JPEG", quality=90, optimize=True)
        except Exception as e:
            print(f"[aviso] story de '{o['nome'][:40]}' não foi gerado: {e}")
            continue
        fila.append({"id": o["id"], "arquivo": f"docs/stories/{nome}", "nome": o["nome"][:80],
                     "criado_em": datetime.now(BRT).isoformat()})
        feitos += 1
    FILA.parent.mkdir(exist_ok=True)
    FILA.write_text(json.dumps(fila, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Stories na fila do Instagram: {len(fila)} (+{feitos} novos)")
    return feitos


def limpar_antigos(dias=3):
    """Apaga artes velhas para o repositório não crescer."""
    if not PASTA.exists():
        return
    limite = datetime.now().timestamp() - dias * 86400
    pendentes = {Path(i["arquivo"]).name for i in _carregar_fila()}
    for f in PASTA.glob("*.jpg"):
        if f.name not in pendentes and f.stat().st_mtime < limite:
            f.unlink()
