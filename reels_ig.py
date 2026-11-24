"""Monta um reel (vídeo vertical 1080x1920, ~15s) com as melhores ofertas e põe na fila.

Roteiro do vídeo:
  1. Abertura (2s): "3 achadinhos até R$ X" com as fotos
  2. Um produto por vez (3s cada): foto com zoom, nome, preço e desconto
  3. Final (3s): chamada para o canal do Telegram

O vídeo fica em docs/reels/ (o Instagram exige link público) e a fila em
data/reels_pendentes.json. Quem publica é o publicar_stories.py.

Teste no PC:  python reels_ig.py --teste   (gera data/reel_teste.mp4 com produtos de exemplo)
"""
import json
import math
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from stories_ig import (BLACK, BOLD, MARCA, MED, T, TEXTO, CINZA, LARANJA, SOBRE, CARTAO,
                        _brl, _foto, _fundo, _nome_curto, _quebrar)

BASE = Path(__file__).parent
PASTA = BASE / "docs" / "reels"
FILA = BASE / "data" / "reels_pendentes.json"
FEITOS = BASE / "data" / "reels_publicados.json"
BRT = timezone(timedelta(hours=-3))
W, H, FPS = 1080, 1920, 30
LULUBA = T["marca"] == "Luluba"
VINHO = (158, 74, 92) if LULUBA else TEXTO

# área segura: o Instagram cobre o rodapé (legenda) e a lateral direita (botões)
TOPO, LIMITE_BAIXO = 230, 1480


def _ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise RuntimeError("ffmpeg não encontrado. Rode: pip install imageio-ffmpeg")


def _ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def _pill(d, x, y, texto, tam=30):
    f = BOLD(tam)
    w = d.textlength(texto, font=f)
    d.rounded_rectangle((x, y, x + w + 48, y + 68), radius=34 if LULUBA else 12, fill=LARANJA)
    d.text((x + 24, y + 34), texto, font=f, fill=SOBRE, anchor="lm")


def _topo(d, selo):
    _pill(d, 90, TOPO - 34, selo)
    d.text((W - 90, TOPO), T["marca"], font=MARCA(56 if LULUBA else 40), fill=VINHO, anchor="rm")


def _arredondar(img, raio):
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, img.width, img.height), radius=raio, fill=255)
    out = Image.new("RGBA", img.size)
    out.paste(img, (0, 0), m)
    return out


def _preco(d, x, base, valor, grande=170, centavos=True):
    inteiro, cent = _brl(valor).split(",")
    d.text((x, base - grande * 0.47), "R$", font=BLACK(int(grande * 0.34)), fill=LARANJA, anchor="ls")
    xi = x + d.textlength("R$", font=BLACK(int(grande * 0.34))) + 12
    d.text((xi, base), inteiro, font=BLACK(grande), fill=LARANJA, anchor="ls")
    if centavos:
        d.text((xi + d.textlength(inteiro, font=BLACK(grande)) + 4, base - grande * 0.46), "," + cent,
               font=BLACK(int(grande * 0.48)), fill=LARANJA, anchor="ls")


# ---------------- cenas ----------------
class Cena:
    """Cada cena devolve um quadro (Image RGB) para o tempo t em segundos."""
    dur = 3.0

    def quadro(self, t):
        raise NotImplementedError


class Abertura(Cena):
    def __init__(self, ofertas, fotos):
        self.dur = 2.2
        teto = max(o["preco"] for o in ofertas)
        teto = int(math.ceil(teto / 10.0) * 10)
        self.base = _fundo()
        d = ImageDraw.Draw(self.base)
        _topo(d, "ACHADINHOS DA SHOPEE" if LULUBA else "OFERTAS DO DIA")
        n = len(ofertas)
        d.text((90, 420), f"{n} achadinhos" if LULUBA else f"{n} ofertas", font=BLACK(130), fill=TEXTO)
        d.text((90, 570), "até", font=MARCA(90) if LULUBA else BLACK(90), fill=VINHO)
        _preco(d, 90 + d.textlength("até ", font=MARCA(90) if LULUBA else BLACK(90)), 700, teto, 150, centavos=False)
        d.text((90, 760), "que valem a pena hoje", font=MED(44), fill=CINZA)
        # miniaturas
        self.minis = []
        lado = (W - 180 - 30 * (n - 1)) // n
        for i, f in enumerate(fotos):
            card = Image.new("RGB", (lado, lado), CARTAO)
            if f:
                card = ImageOps.fit(f, (lado, lado), centering=(0.5, 0.3))
            self.minis.append((_arredondar(card, 30), 90 + i * (lado + 30)))
        self.y_min = 880

    def quadro(self, t):
        img = self.base.copy()
        for i, (m, x) in enumerate(self.minis):
            p = _ease((t - 0.15 * i) / 0.45)
            if p <= 0:
                continue
            y = int(self.y_min + (1 - p) * 120)
            img.paste(m, (x, y), m)
        return img


class Produto(Cena):
    def __init__(self, o, foto, i, n):
        self.dur = 3.2
        self.o = o
        self.base = _fundo()
        d = ImageDraw.Draw(self.base)
        _topo(d, f"ACHADINHO {i}/{n}" if LULUBA else f"OFERTA {i}/{n}")
        self.box = (90, 300, W - 90, 1090)
        x0, y0, x1, y1 = self.box
        d.rounded_rectangle(self.box, radius=44, fill=CARTAO)
        self.foto = None
        if foto:
            bw, bh = x1 - x0, y1 - y0
            # foto inteira centralizada; se for de pessoa (vertical), preenche o quadro
            if foto.height >= foto.width * 1.1:
                self.foto = ImageOps.fit(foto, (int(bw * 1.12), int(bh * 1.12)), centering=(0.5, 0.25))
            else:
                self.foto = ImageOps.contain(foto, (int((bw - 40) * 1.12), int((bh - 40) * 1.12)))
        # textos fixos
        y = y1 + 40
        for linha in _quebrar(d, _nome_curto(o["nome"]), BOLD(50), W - 180, 2):
            d.text((90, y), linha, font=BOLD(50), fill=TEXTO)
            y += 62
        self.y_preco = y + 20
        if o.get("preco_original") and o["preco_original"] > o["preco"]:
            de = f"De R$ {_brl(o['preco_original'])}"
            d.text((90, self.y_preco), de, font=MED(40), fill=CINZA)
            xa = 90 + d.textlength("De ", font=MED(40))
            d.line((xa, self.y_preco + 26, 90 + d.textlength(de, font=MED(40)), self.y_preco + 26), fill=CINZA, width=4)
            self.y_preco += 56
        # camada do preço (entra com "pulo")
        self.camada = Image.new("RGBA", (W, 260), (0, 0, 0, 0))
        dc = ImageDraw.Draw(self.camada)
        _preco(dc, 90, 190, o["preco"], 180)
        meta = []
        if o.get("nota"):
            meta.append(f"Nota {o['nota']:.1f}".replace(".", ","))
        if o.get("vendas"):
            v = int(o["vendas"])
            meta.append(f"{v // 1000} mil+ vendidos" if v >= 1000 and v % 1000 == 0 else f"{v:,} vendidos".replace(",", "."))
        self.meta = " · ".join(meta)

    def quadro(self, t):
        img = self.base.copy()
        x0, y0, x1, y1 = self.box
        bw, bh = x1 - x0, y1 - y0
        if self.foto:
            z = 1.0 + 0.10 * (t / self.dur)  # zoom lento (efeito Ken Burns)
            fw, fh = int(self.foto.width / 1.12 * z), int(self.foto.height / 1.12 * z)
            f = self.foto.resize((fw, fh), Image.BILINEAR)
            tela = Image.new("RGB", (bw, bh), CARTAO)  # tudo fica dentro do quadro
            oy = int((bh - f.height) * 0.3) if f.height > bh else (bh - f.height) // 2
            tela.paste(f, ((bw - f.width) // 2, oy))
            tela = _arredondar(tela, 44)
            img.paste(tela, (x0, y0), tela)
        d = ImageDraw.Draw(img)
        # selo de desconto
        if self.o.get("desconto"):
            p = _ease((t - 0.25) / 0.35)
            if p > 0:
                r = int(112 * (0.6 + 0.4 * p))
                cx, cy = x1 - 130, y0 + 130
                d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=LARANJA)
                d.text((cx, cy - 18), f"{self.o['desconto']}%", font=BLACK(int(78 * r / 112)), fill=SOBRE, anchor="mm")
                d.text((cx, cy + 44 * r / 112), "OFF", font=BLACK(int(38 * r / 112)), fill=SOBRE, anchor="mm")
        # preço com pulo
        p = (t - 0.45) / 0.4
        if p > 0:
            s = 1 + 0.12 * math.sin(min(p, 1) * math.pi) if p < 1 else 1
            cam = self.camada if s == 1 else self.camada.resize((int(W * s), int(260 * s)), Image.BILINEAR)
            img.paste(cam, (int(90 - 90 * s), self.y_preco - 20 - int(130 * (s - 1))), cam)
        if self.meta and t > 0.9:
            fm = BOLD(32)
            y = self.y_preco + 230
            w = d.textlength(self.meta, font=fm)
            d.rounded_rectangle((90, y, 90 + w + 40, y + 60), radius=14, fill=CARTAO, outline=LARANJA, width=3)
            d.text((110, y + 30), self.meta, font=fm, fill=TEXTO, anchor="lm")
        return img


class Final(Cena):
    def __init__(self, canal, arroba):
        self.dur = 3.0
        self.base = _fundo()
        d = ImageDraw.Draw(self.base)
        _topo(d, "NÃO PERCA")
        d.text((90, 430), "Quer os links?", font=BLACK(110), fill=TEXTO)
        d.text((90, 580), "Estão no canal", font=MARCA(84) if LULUBA else BLACK(84), fill=VINHO)
        d.text((90, 690), "do Telegram, de graça", font=MED(46), fill=CINZA)
        self.card = Image.new("RGBA", (W - 180, 300), (0, 0, 0, 0))
        dc = ImageDraw.Draw(self.card)
        dc.rounded_rectangle((0, 0, W - 180, 300), radius=36, fill=VINHO if LULUBA else LARANJA)
        dc.text((50, 70), "toque no link da bio", font=MED(38), fill=SOBRE, anchor="lm")
        link = "t.me/" + canal.lstrip("@") if canal.startswith("@") else canal
        dc.text((50, 160), link, font=BOLD(66), fill=SOBRE, anchor="lm")
        dc.text((50, 240), "ofertas novas o dia todo", font=MED(34), fill=SOBRE, anchor="lm")
        palavra = (os.getenv("REELS_PALAVRA") or "").strip().upper()
        if palavra:
            d.text((90, 1230), f"ou comenta \"{palavra}\"", font=BOLD(54), fill=TEXTO)
            d.text((90, 1300), "que eu te mando no direct", font=MED(40), fill=CINZA)
        else:
            d.text((90, 1250), "Salva pra não perder", font=BOLD(42), fill=TEXTO)
        d.text((90, 1370), arroba, font=BOLD(36), fill=LARANJA)

    def quadro(self, t):
        img = self.base.copy()
        p = _ease(t / 0.5)
        y = int(860 + (1 - p) * 140)
        img.paste(self.card, (90, y), self.card)
        return img


# ---------------- vídeo ----------------
def montar(ofertas, saida, canal, arroba, fotos=None):
    """Gera o MP4. `fotos` (opcional) = lista de Image já carregadas, na mesma ordem."""
    fotos = fotos or [_foto(o.get("imagem")) for o in ofertas]
    cenas = [Abertura(ofertas, fotos)]
    cenas += [Produto(o, f, i + 1, len(ofertas)) for i, (o, f) in enumerate(zip(ofertas, fotos))]
    cenas.append(Final(canal, arroba))

    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    cmd = [_ffmpeg(), "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
           "-shortest", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(saida)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    TRANS = 6  # quadros de transição (fade)
    anterior = None
    for c in cenas:
        n = int(c.dur * FPS)
        for k in range(n):
            q = c.quadro(k / FPS)
            if anterior is not None and k < TRANS:
                q = Image.blend(anterior, q, (k + 1) / (TRANS + 1))
            proc.stdin.write(q.convert("RGB").tobytes())
        anterior = c.quadro((n - 1) / FPS).convert("RGB")
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg falhou ao gerar o vídeo")
    return saida


def legenda(ofertas, canal):
    num = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    link = "t.me/" + canal.lstrip("@") if canal.startswith("@") else canal
    if LULUBA:
        topo = "Achadinhos lindos da Shopee que valem a pena hoje 💕"
        tags = "#achadinhosshopee #shopee #modafeminina #achadinhos #promocao #lookdodia #lulubastore"
    else:
        topo = "Ofertas de tecnologia na Shopee que valem a pena hoje 🔥"
        tags = "#achadinhosshopee #shopee #tecnologia #ofertas #promocao #setupgamer #techbarato"
    linhas = [topo, ""]
    for i, o in enumerate(ofertas):
        linhas.append(f"{num[i]} {_nome_curto(o['nome'])}: R$ {_brl(o['preco'])}"
                      + (f" ({o['desconto']}% OFF)" if o.get("desconto") else ""))
    palavra = (os.getenv("REELS_PALAVRA") or "").strip().upper()
    linhas += [""] + ([f"👇 Comenta \"{palavra}\" que eu te mando no direct o canal com as melhores ofertas do dia!"] if palavra else []) + [
               f"🔗 Os links estão no canal do Telegram: {link} (link na bio)",
               "💾 Salva pra não perder e manda pra uma amiga!" if LULUBA else "💾 Salva e manda pra quem está montando o setup!",
               "", "Preços de hoje, podem mudar a qualquer momento.", "", tags]
    return "\n".join(linhas)


def _ler(path, padrao):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return padrao


def hora_de_fazer(hora_alvo):
    """Faz 1 reel por dia, na primeira rodada depois da hora escolhida."""
    agora = datetime.now(BRT)
    if agora.hour < hora_alvo:
        return False
    hoje = agora.date().isoformat()
    todos = _ler(FILA, []) + _ler(FEITOS, [])
    return not any(r.get("criado_em", "").startswith(hoje) for r in todos)


def enfileirar(vitrine, canal, arroba, quantidade=3):
    """Pega as melhores ofertas postadas nas últimas 12h e gera o reel do dia."""
    agora = datetime.now(BRT)
    recentes = [o for o in vitrine if o.get("postado_em") and o.get("imagem")
                and agora - datetime.fromisoformat(o["postado_em"]) < timedelta(hours=12)]
    recentes.sort(key=lambda o: (o.get("desconto", 0), o.get("vendas", 0)), reverse=True)
    escolhidos, cats = [], set()
    for o in recentes:  # variedade: uma de cada categoria quando der
        if o.get("categoria") not in cats:
            escolhidos.append(o); cats.add(o.get("categoria"))
        if len(escolhidos) >= quantidade:
            break
    for o in recentes:
        if len(escolhidos) >= quantidade:
            break
        if o not in escolhidos:
            escolhidos.append(o)
    if len(escolhidos) < 2:
        print("Reel: poucas ofertas recentes, fica para a próxima rodada.")
        return False
    nome = f"reel-{agora:%Y%m%d-%H%M}.mp4"
    try:
        montar(escolhidos, PASTA / nome, canal, arroba)
    except Exception as e:
        print(f"[aviso] reel não foi gerado: {e}")
        return False
    fila = _ler(FILA, [])
    fila.append({"arquivo": f"docs/reels/{nome}", "legenda": legenda(escolhidos, canal),
                 "criado_em": agora.isoformat()})
    FILA.write_text(json.dumps(fila, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"🎬 Reel do dia gerado: {nome} ({len(escolhidos)} ofertas)")
    return True


def limpar_antigos(dias=2):
    if not PASTA.exists():
        return
    limite = datetime.now().timestamp() - dias * 86400
    pendentes = {Path(i["arquivo"]).name for i in _ler(FILA, [])}
    for f in PASTA.glob("*.mp4"):
        if f.name not in pendentes and f.stat().st_mtime < limite:
            f.unlink()


if __name__ == "__main__":
    if "--teste" in sys.argv:
        exemplo = [
            {"nome": "Vestido Midi 100% Algodão com Bolsos", "preco": 34.99, "preco_original": 145.79, "desconto": 76, "nota": 4.8, "vendas": 1077},
            {"nome": "Biquíni Cortininha Fio Dental Regulável", "preco": 20.10, "preco_original": 80.40, "desconto": 75, "nota": 4.6, "vendas": 1471},
            {"nome": "Vestido Longo Frente Única com Decote", "preco": 32.48, "preco_original": 116.00, "desconto": 72, "nota": 4.9, "vendas": 2087},
        ]
        fotos = [Image.new("RGB", (800, 1000), (230, 200, 190)) for _ in exemplo]
        out = montar(exemplo, BASE / "data" / "reel_teste.mp4", os.getenv("TELEGRAM_CHAT_ID", "@lulubastore"),
                     os.getenv("IG_HANDLE", "@luluba.store"), fotos)
        print("Vídeo de teste:", out)
        print(legenda(exemplo, "@lulubastore"))
