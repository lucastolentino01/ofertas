"""Teste rápido: confere se a API da Shopee e o Telegram estão funcionando."""
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "configuracao.txt", encoding="utf-8-sig")
load_dotenv(Path(__file__).parent / ".env")
ok = True


def linha(t=""):
    print(t)


linha("=" * 50)
linha(" TESTE DO BOT DE OFERTAS — Tech Barato BR")
linha("=" * 50)

# 1. Shopee
app_id, secret = os.getenv("SHOPEE_APP_ID", "").strip(), os.getenv("SHOPEE_APP_SECRET", "").strip()
linha("\n[1] API da Shopee")
if not app_id or not secret:
    linha("   ❌ Falta SHOPEE_APP_ID ou SHOPEE_APP_SECRET no arquivo configuracao.txt"); ok = False
else:
    from shopee_api import ShopeeAffiliate
    try:
        api = ShopeeAffiliate(app_id, secret)
        prods = api.buscar_produtos("ssd", sort_type=2, limit=3)
        if not prods:
            linha("   ⚠️ Conectou, mas não voltou produto. Tente outra palavra em KEYWORDS.")
        for p in prods:
            com = f" | comissão {float(p['commissionRate'])*100:.0f}%" if p.get('commissionRate') else ""
            linha(f"   ✅ {p['productName'][:55]}  |  R$ {p.get('priceMin')}{com}")
        if prods:
            linha(f"   (campos usados: {'completos' if api._campos and 'shopName' in api._campos else 'reduzidos'})")
            link = api.link_curto(prods[0]["productLink"], sub_id="teste")
            linha(f"   ✅ Link de afiliado gerado: {link}")
    except Exception as e:
        linha(f"   ❌ Erro: {e}"); ok = False
        linha("\n   Diagnóstico (mande um print desta parte para o Claude):")
        try:
            for nome, passou, msg in api.diagnostico():
                linha(f"   {'✅' if passou else '❌'} {nome}{'' if passou else ' -> ' + msg[:90]}")
        except Exception as e2:
            linha(f"   (diagnóstico falhou: {e2})")

# 2. Telegram
tok, chat = os.getenv("TELEGRAM_BOT_TOKEN", "").strip(), os.getenv("TELEGRAM_CHAT_ID", "").strip()
linha("\n[2] Telegram")
if not tok or not chat:
    linha("   ❌ Falta TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID no arquivo configuracao.txt"); ok = False
else:
    try:
        me = requests.get(f"https://api.telegram.org/bot{tok}/getMe", timeout=20).json()
        if not me.get("ok"):
            linha("   ❌ Token do bot inválido. Copie de novo do @BotFather."); ok = False
        else:
            linha(f"   ✅ Bot: @{me['result']['username']}")
            ch = requests.get(f"https://api.telegram.org/bot{tok}/getChat", params={"chat_id": chat}, timeout=20).json()
            if not ch.get("ok"):
                linha(f"   ❌ Não achei o canal {chat}. Confira o @ e se o bot é ADMINISTRADOR do canal."); ok = False
            else:
                linha(f"   ✅ Canal: {ch['result'].get('title')}")
                adm = requests.get(f"https://api.telegram.org/bot{tok}/getChatMember",
                                   params={"chat_id": chat, "user_id": me["result"]["id"]}, timeout=20).json()
                status = adm.get("result", {}).get("status")
                if status in ("administrator", "creator"):
                    linha("   ✅ O bot é administrador e pode postar")
                else:
                    linha("   ❌ O bot NÃO é administrador do canal. Adicione-o como admin com 'Publicar mensagens'."); ok = False
    except Exception as e:
        linha(f"   ❌ Erro: {e}"); ok = False

linha("\n" + "=" * 50)
linha(" ✅ TUDO CERTO! Pode rodar o bot." if ok else " ❌ Corrija os itens acima e rode o teste de novo.")
linha("=" * 50)
