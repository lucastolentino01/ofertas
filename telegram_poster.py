"""Publica ofertas em um canal/grupo do Telegram."""
import html

import requests


def formatar_preco(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def montar_mensagem(oferta: dict) -> str:
    nome = html.escape(oferta["nome"][:120])
    linhas = [f"🔥 <b>{nome}</b>", ""]
    if oferta.get("desconto"):
        linhas.append(f"🏷️ <b>{oferta['desconto']}% OFF</b>")
    if oferta.get("preco_original") and oferta["preco_original"] > oferta["preco"]:
        linhas.append(f"De <s>{formatar_preco(oferta['preco_original'])}</s>")
    linhas.append(f"💰 Por <b>{formatar_preco(oferta['preco'])}</b>")
    extras = []
    if oferta.get("nota"):
        extras.append(f"⭐ {oferta['nota']:.1f}")
    if oferta.get("vendas"):
        extras.append(f"🛒 {oferta['vendas']} vendidos")
    if extras:
        linhas.append(" · ".join(extras))
    linhas += ["", f"👉 <a href=\"{oferta['link']}\">COMPRAR NA SHOPEE</a>", "",
               "<i>Preço pode mudar a qualquer momento.</i>"]
    return "\n".join(linhas)


class TelegramPoster:
    def __init__(self, token: str, chat_id: str):
        self.base = f"https://api.telegram.org/bot{token}"
        self.chat_id = chat_id

    def postar(self, oferta: dict) -> None:
        texto = montar_mensagem(oferta)
        if oferta.get("imagem"):
            r = requests.post(f"{self.base}/sendPhoto", data={
                "chat_id": self.chat_id, "photo": oferta["imagem"],
                "caption": texto, "parse_mode": "HTML"}, timeout=30)
            if r.ok:
                return
        # fallback: só texto
        r = requests.post(f"{self.base}/sendMessage", data={
            "chat_id": self.chat_id, "text": texto, "parse_mode": "HTML",
            "disable_web_page_preview": False}, timeout=30)
        if not r.ok:
            raise RuntimeError(f"Telegram recusou: {r.text}")
