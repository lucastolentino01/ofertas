"""Publica no Instagram os stories que estão na fila (API oficial do Instagram).

Uso:
  python publicar_stories.py            -> publica a fila (roda no GitHub)
  python publicar_stories.py --testar   -> só confere o token e a conta (use no PC)

Precisa de (Secrets no GitHub, ou configuracao.txt no PC):
  IG_ACCESS_TOKEN  token do app Meta (login pelo Instagram)
  IG_USER_ID       opcional: o bot descobre sozinho
Opcionais:
  TELEGRAM_BOT_TOKEN + TELEGRAM_MEU_ID   avisos no seu Telegram (token vencendo, erros)
  GH_PAT           renova o token sozinho no GitHub (veja o guia)
"""
import argparse
import base64
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BASE = Path(__file__).parent
FILA = BASE / "data" / "stories_pendentes.json"
FEITOS = BASE / "data" / "stories_publicados.json"
ESTADO = BASE / "data" / "ig_token.json"
BRT = timezone(timedelta(hours=-3))

try:
    from dotenv import load_dotenv
    load_dotenv(BASE / "configuracao.txt", encoding="utf-8-sig")
    load_dotenv(BASE / ".env")
except ImportError:
    pass


def cfg(nome, padrao=None):
    v = os.getenv(nome)
    return v.strip() if v and v.strip() else padrao


VERSAO = cfg("IG_API_VERSION", "v26.0")
API = f"https://graph.instagram.com/{VERSAO}"


def tipo_token(token):
    """'sistema' = token do Usuário do Sistema (EAA..., não vence, usa graph.facebook.com)
    'instagram' = token do login do Instagram (IG..., vence em 60 dias)."""
    return "sistema" if token.startswith("EAA") else "instagram"


def usar_host(token):
    global API
    host = "graph.facebook.com" if tipo_token(token) == "sistema" else "graph.instagram.com"
    API = f"https://{host}/{VERSAO}"


def ler(path, padrao):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return padrao


def salvar(path, dados):
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def avisar(texto):
    """Mensagem no seu Telegram pessoal (não no canal)."""
    print("[AVISO]", texto)
    tok, eu = cfg("TELEGRAM_BOT_TOKEN"), cfg("TELEGRAM_MEU_ID")
    if tok and eu:
        try:
            requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                          data={"chat_id": eu, "text": "🤖 Bot Tech Barato (Instagram)\n\n" + texto}, timeout=20)
        except Exception:
            pass


class ErroIG(Exception):
    def __init__(self, msg, code=None):
        super().__init__(msg)
        self.code = code


def ig(metodo, caminho, token, **params):
    params["access_token"] = token
    url = caminho if caminho.startswith("http") else f"{API}/{caminho.lstrip('/')}"
    r = (requests.get(url, params=params, timeout=60) if metodo == "GET"
         else requests.post(url, data=params, timeout=60))
    try:
        body = r.json()
    except ValueError:
        raise ErroIG(f"Resposta inválida do Instagram (HTTP {r.status_code})")
    if "error" in body:
        e = body["error"]
        raise ErroIG(f"{e.get('message')} (código {e.get('code')})", e.get("code"))
    return body


# ---------------- token ----------------
def _hash(t):
    return hashlib.sha256(t.encode()).hexdigest()[:16]


def atualizar_secret_github(novo_token):
    """Grava o token renovado no Secret IG_ACCESS_TOKEN (precisa de GH_PAT)."""
    pat, repo = cfg("GH_PAT"), os.getenv("GITHUB_REPOSITORY")
    if not pat or not repo:
        return False
    try:
        from nacl import encoding, public
    except ImportError:
        print("[aviso] pynacl não instalado; não dá para atualizar o Secret")
        return False
    h = {"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json"}
    k = requests.get(f"https://api.github.com/repos/{repo}/actions/secrets/public-key", headers=h, timeout=30)
    if not k.ok:
        print("[aviso] GH_PAT sem permissão para ler a chave dos Secrets:", k.status_code)
        return False
    chave = k.json()
    box = public.SealedBox(public.PublicKey(chave["key"].encode(), encoding.Base64Encoder()))
    cifrado = base64.b64encode(box.encrypt(novo_token.encode())).decode()
    r = requests.put(f"https://api.github.com/repos/{repo}/actions/secrets/IG_ACCESS_TOKEN", headers=h,
                     json={"encrypted_value": cifrado, "key_id": chave["key_id"]}, timeout=30)
    return r.status_code in (201, 204)


def cuidar_do_token(token):
    """Renova o token 1x por semana e avisa antes de vencer."""
    if tipo_token(token) == "sistema":
        return token  # token do Usuário do Sistema não vence
    est = ler(ESTADO, {})
    agora = datetime.now(BRT)
    if est.get("hash") != _hash(token):  # token novo colado pelo usuário
        est = {"hash": _hash(token), "visto_em": agora.isoformat(),
               "vence_em": (agora + timedelta(days=59)).isoformat()}
    ultima = datetime.fromisoformat(est.get("renovado_em", est["visto_em"]))
    if agora - ultima > timedelta(days=7):
        try:
            r = ig("GET", "https://graph.instagram.com/refresh_access_token", token, grant_type="ig_refresh_token")
            novo = r.get("access_token", token)
            est["renovado_em"] = agora.isoformat()
            est["vence_em"] = (agora + timedelta(seconds=int(r.get("expires_in", 5184000)))).isoformat()
            if novo != token:
                if atualizar_secret_github(novo):
                    print("Token renovado e salvo no GitHub.")
                    est["hash"] = _hash(novo)
                    token = novo
                else:
                    # o token antigo continua valendo até a data dele
                    est["vence_em"] = (datetime.fromisoformat(est["visto_em"]) + timedelta(days=59)).isoformat()
            else:
                print("Token renovado (mais 60 dias).")
        except ErroIG as e:
            print("[aviso] não consegui renovar o token agora:", e)
    vence = datetime.fromisoformat(est["vence_em"])
    dias = (vence - agora).days
    if dias <= 10 and est.get("avisado_em", "")[:10] != agora.date().isoformat():
        avisar(f"O token do Instagram vence em {max(dias, 0)} dia(s). Gere um novo no painel da Meta "
               f"e cole no Secret IG_ACCESS_TOKEN do GitHub (guia: INSTAGRAM-STORIES.md, Parte 5).")
        est["avisado_em"] = agora.isoformat()
    salvar(ESTADO, est)
    return token


def descobrir_usuario(token, verbose=False):
    """Devolve {'user_id','username','account_type'} da conta do Instagram."""
    log = (lambda m: print("   ·", m)) if verbose else (lambda m: None)
    if tipo_token(token) == "instagram":
        return ig("GET", "me", token, fields="user_id,username,account_type")

    candidatos = []
    uid = cfg("IG_USER_ID")
    # 1) contas ligadas a Páginas
    try:
        pags = ig("GET", "me/accounts", token, fields="instagram_business_account{id,username}").get("data", [])
        for pg in pags:
            c = pg.get("instagram_business_account")
            if c:
                candidatos.append(c["id"])
        log(f"me/accounts: {len(pags)} página(s)")
    except ErroIG as e:
        log(f"me/accounts: {e}")
    # 2) contas do portfólio
    negocios = [cfg("IG_BUSINESS_ID")] if cfg("IG_BUSINESS_ID") else []
    try:
        negocios += [n["id"] for n in ig("GET", "me/businesses", token, fields="id").get("data", [])]
        log(f"portfólios encontrados: {negocios or 'nenhum'}")
    except ErroIG as e:
        log(f"me/businesses: {e}")
    for n in dict.fromkeys(filter(None, negocios)):
        for edge in ("instagram_business_accounts", "owned_instagram_accounts", "instagram_accounts", "owned_pages", "client_pages"):
            try:
                campos = "id,name" if "pages" in edge else "id,username"
                contas = ig("GET", f"{n}/{edge}", token, fields=campos).get("data", [])
                log(f"{edge}: {[(c.get('username') or c.get('name'), c['id']) for c in contas]}")
                candidatos += [c["id"] for c in contas]
            except ErroIG as e:
                log(f"{edge}: {e}")
    if uid:
        candidatos.append(uid)
    # 3) testa cada candidato como conta de publicação
    for cid in dict.fromkeys(candidatos):
        # descobre que tipo de objeto é esse número
        try:
            meta = ig("GET", cid, token, metadata="1", fields="id").get("metadata", {}).get("type")
            log(f"{cid}: tipo {meta}")
        except ErroIG as e:
            log(f"{cid}: tipo ? ({e})")
        # se for uma Página, pega a conta do Instagram ligada a ela
        try:
            c = ig("GET", cid, token, fields="instagram_business_account{id,username}").get("instagram_business_account")
            if c:
                log(f"{cid}: Página com Instagram {c.get('username')} ({c['id']})")
                candidatos.append(c["id"])
                cid = c["id"]
        except ErroIG:
            pass
        try:
            ig("GET", f"{cid}/content_publishing_limit", token)
            try:
                nome = ig("GET", cid, token, fields="username").get("username")
            except ErroIG:
                nome = None
            log(f"{cid}: pode publicar ✔")
            return {"user_id": cid, "username": nome or "techbarato.ofertas", "account_type": "BUSINESS"}
        except ErroIG as e:
            log(f"{cid}: não serve para publicar ({e})")
    raise ErroIG("Não achei a conta do Instagram com esse token. Veja os detalhes acima e mande um print ao Claude.")


# ---------------- publicação ----------------
def url_publica(arquivo):
    base = cfg("IG_IMAGE_BASE_URL")
    if base:
        return base.rstrip("/") + "/" + arquivo.split("docs/", 1)[-1]
    repo = os.getenv("GITHUB_REPOSITORY")
    ramo = os.getenv("GITHUB_REF_NAME", "main")
    if not repo:
        raise RuntimeError("Sem GITHUB_REPOSITORY: rode no GitHub ou defina IG_IMAGE_BASE_URL")
    return f"https://raw.githubusercontent.com/{repo}/{ramo}/{arquivo}"


def esperar_url(url, limite=120):
    fim = time.time() + limite
    while time.time() < fim:
        try:
            r = requests.head(url, timeout=20, allow_redirects=True)
            if r.ok:
                return True
        except requests.RequestException:
            pass
        time.sleep(10)
    return False


def publicar_um(token, uid, url):
    c = ig("POST", f"{uid}/media", token, image_url=url, media_type="STORIES")
    cid = c["id"]
    for _ in range(12):  # até ~1 min processando
        st = ig("GET", cid, token, fields="status_code").get("status_code")
        if st == "FINISHED":
            break
        if st in ("ERROR", "EXPIRED"):
            raise ErroIG(f"Instagram não aceitou a imagem (status {st})")
        time.sleep(5)
    return ig("POST", f"{uid}/media_publish", token, creation_id=cid)["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--testar", action="store_true")
    args = ap.parse_args()

    token = cfg("IG_ACCESS_TOKEN")
    if not token:
        print("Instagram desligado (sem IG_ACCESS_TOKEN). Nada a fazer.")
        return
    usar_host(token)

    if args.testar:
        print("=" * 50, "\n TESTE DO INSTAGRAM\n" + "=" * 50)
        print(f" Token lido: começa com '{token[:4]}', termina com '{token[-3:]}', {len(token)} caracteres")
        problemas = []
        if not token.startswith(("EAA", "IG")):
            problemas.append("não começa com EAA (nem IG): confira se não ficou texto de exemplo, parênteses ou aspas")
        if any(c in token for c in " ()\"'<>"):
            problemas.append("tem espaço, parênteses ou aspas no meio: apague e cole só o token")
        if len(token) < 100:
            problemas.append("está curto demais: parece cortado. Copie o token inteiro de novo")
        for p in problemas:
            print(" ⚠️", p)
        if problemas:
            print("\n Corrija a linha IG_ACCESS_TOKEN= no .env (ou configuracao.txt) e rode de novo.")
            return
        try:
            me = descobrir_usuario(token, verbose=True)
            print(f" ✅ Conta: @{me.get('username')}  (id {me.get('user_id')})")
            print(f" ✅ Tipo de token: {'Usuário do Sistema (não vence)' if tipo_token(token) == 'sistema' else 'Login do Instagram (vence em 60 dias)'}")
            if tipo_token(token) == "sistema" and not cfg("IG_USER_ID"):
                print(f"    Dica: cadastre IG_USER_ID = {me.get('user_id')} nos Secrets do GitHub.")
            tipo = me.get("account_type")
            if tipo == "BUSINESS":
                print(" ✅ Conta comercial: pode publicar stories")
            else:
                print(f" ⚠️ Tipo da conta: {tipo}. Para stories, mude para conta COMERCIAL (Empresa).")
            lim = ig("GET", f"{me.get('user_id')}/content_publishing_limit", token, fields="quota_usage,config")
            d = (lim.get("data") or [{}])[0]
            print(f" ✅ Publicações nas últimas 24h: {d.get('quota_usage', '?')} de {d.get('config', {}).get('quota_total', '?')}")
            print("\n Tudo certo! Agora é só cadastrar o token no GitHub (Parte 4 do guia).")
        except ErroIG as e:
            print(" ❌", e)
            if e.code == 190:
                print("    Token inválido ou vencido: gere um novo no painel da Meta.")
        return

    try:
        token = cuidar_do_token(token)
        uid = descobrir_usuario(token)["user_id"]
    except ErroIG as e:
        avisar(f"Não consegui acessar o Instagram: {e}. Se for token vencido (código 190), gere um novo.")
        sys.exit(0)

    fila = ler(FILA, [])
    feitos = ler(FEITOS, [])
    agora = datetime.now(BRT)
    maximo = int(cfg("IG_MAX_POR_RODADA", 2))
    restantes, publicados = [], 0

    for item in fila:
        idade = agora - datetime.fromisoformat(item["criado_em"])
        if idade > timedelta(hours=12):
            print(f"Descartado (oferta velha, o preço pode ter mudado): {item['nome'][:50]}")
            continue
        if publicados >= maximo:
            restantes.append(item)
            continue
        url = url_publica(item["arquivo"])
        if not esperar_url(url):
            print("Imagem ainda não está pública, tento na próxima rodada:", url)
            restantes.append(item)
            continue
        try:
            mid = publicar_um(token, uid, url)
            publicados += 1
            feitos.append({**item, "media_id": mid, "publicado_em": agora.isoformat()})
            print(f"✅ Story publicado: {item['nome'][:60]}")
            time.sleep(20)
        except ErroIG as e:
            item["tentativas"] = item.get("tentativas", 0) + 1
            print(f"❌ Falhou ({item['tentativas']}ª vez): {e}")
            if e.code == 190:
                avisar("Token do Instagram inválido ou vencido. Gere um novo no painel da Meta e "
                       "atualize o Secret IG_ACCESS_TOKEN no GitHub.")
                restantes.append(item)
                break
            if item["tentativas"] < 3:
                restantes.append(item)
            else:
                avisar(f"Desisti de publicar um story após 3 tentativas: {item['nome'][:60]}\nErro: {e}")

    salvar(FILA, restantes)
    salvar(FEITOS, feitos[-200:])
    print(f"Stories publicados agora: {publicados}. Na fila: {len(restantes)}.")


if __name__ == "__main__":
    main()
