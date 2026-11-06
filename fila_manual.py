"""Modo manual: lê produtos da planilha data/fila.csv (abre no Excel).

Colunas (separadas por ; ):
  nome ; preco ; preco_original ; link ; imagem ; categoria
- nome, preco e link são obrigatórios
- preco aceita "89,90" ou "R$ 89,90"
- link = o seu link de afiliado (gerado em "Link personalizado" no painel)
- imagem é opcional (sem imagem, o Telegram mostra a prévia do link)
"""
import csv
import re
import zlib

CAMPOS = ["nome", "preco", "preco_original", "link", "imagem", "categoria"]


def _preco(txt):
    txt = re.sub(r"[^\d,.]", "", str(txt or ""))
    if not txt:
        return 0.0
    if "," in txt:
        txt = txt.replace(".", "").replace(",", ".")
    try:
        return float(txt)
    except ValueError:
        return 0.0


def _abrir(path):
    for enc in ("utf-8-sig", "cp1252"):  # Excel no Windows costuma salvar em cp1252
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def ler_fila(path):
    if not path.exists():
        print(f"[aviso] {path.name} não existe — nada para postar.")
        return []
    texto = _abrir(path)
    sep = ";" if texto.count(";") >= texto.count(",") else ","
    linhas = list(csv.DictReader(texto.splitlines(), delimiter=sep))
    ofertas = []
    for r in linhas:
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        if not r.get("nome") or not r.get("link"):
            continue
        preco = _preco(r.get("preco"))
        original = _preco(r.get("preco_original")) or None
        desconto = round((1 - preco / original) * 100) if original and original > preco > 0 else 0
        ofertas.append({
            "id": "m" + str(zlib.crc32(r["link"].encode())),
            "nome": r["nome"], "preco": preco, "preco_original": original, "desconto": desconto,
            "imagem": r.get("imagem") or None, "nota": 0, "vendas": 0,
            "link": r["link"], "categoria": r.get("categoria") or "Ofertas",
            "_linha": r,
        })
    return ofertas


def salvar_fila(path, ofertas):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, delimiter=";", extrasaction="ignore")
        w.writeheader()
        for o in ofertas:
            w.writerow({k: o["_linha"].get(k, "") for k in CAMPOS})
