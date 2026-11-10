"""Cliente da API oficial de Afiliados da Shopee Brasil (GraphQL).

Assinatura: SHA256(AppID + Timestamp + Payload + Senha)
Os argumentos vão escritos direto na consulta (sem "variables"),
que é o formato usado nos exemplos oficiais da Shopee.
"""
import hashlib
import json
import time

import requests

ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql"

# Campos em ordem de prioridade. Se a API recusar o conjunto completo,
# o bot tenta automaticamente com menos campos (plano B e C).
CAMPOS_COMPLETOS = ("itemId productName priceMin priceMax priceDiscountRate imageUrl "
                    "ratingStar sales commissionRate shopName productLink offerLink")
CAMPOS_MEDIOS = "itemId productName priceMin imageUrl ratingStar sales commissionRate productLink offerLink"
CAMPOS_MINIMOS = "itemId productName priceMin imageUrl productLink offerLink"


class ShopeeAPIError(Exception):
    def __init__(self, msg, code=None):
        super().__init__(msg)
        self.code = code


def _s(texto):
    """Texto seguro dentro da consulta GraphQL."""
    return json.dumps(str(texto), ensure_ascii=False)


class ShopeeAffiliate:
    def __init__(self, app_id: str, secret: str):
        app_id, secret = (app_id or "").strip(), (secret or "").strip()
        if not app_id or not secret:
            raise ShopeeAPIError("Configure SHOPEE_APP_ID e SHOPEE_APP_SECRET no configuracao.txt")
        self.app_id = app_id
        self.secret = secret
        self._campos = None    # descobre sozinho qual conjunto de campos funciona
        self._variacao = None  # e qual formato de busca a Shopee aceita

    def _call(self, query: str, tentativas: int = 3) -> dict:
        payload = json.dumps({"query": query}, separators=(",", ":"), ensure_ascii=False)
        for tentativa in range(tentativas):
            ts = str(int(time.time()))
            sig = hashlib.sha256((self.app_id + ts + payload + self.secret).encode("utf-8")).hexdigest()
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"SHA256 Credential={self.app_id}, Timestamp={ts}, Signature={sig}",
            }
            r = requests.post(ENDPOINT, data=payload.encode("utf-8"), headers=headers, timeout=30)
            r.raise_for_status()
            body = r.json()
            erros = body.get("errors")
            if not erros:
                return body["data"]
            ext = erros[0].get("extensions") or {}
            code = ext.get("code")
            msg = ext.get("message") or erros[0].get("message")
            if code in (10030, 10000) and tentativa < tentativas - 1:  # limite / instabilidade
                time.sleep(3 * (tentativa + 1))
                continue
            raise ShopeeAPIError(f"Erro da API Shopee ({code}): {msg}", code)
        raise ShopeeAPIError("Falha após várias tentativas")

    # Variações de argumentos da busca: a Shopee às vezes muda o que aceita.
    # O bot testa na ordem e guarda a primeira que funcionar.
    VARIACOES = (
        lambda kw, st, lim, pg: f"keyword: {_s(kw)}, sortType: {int(st)}, page: {int(pg)}, limit: {int(lim)}",
        lambda kw, st, lim, pg: f"keyword: {_s(kw)}, page: {int(pg)}, limit: {int(lim)}",
        lambda kw, st, lim, pg: f"keyword: {_s(kw)}, limit: {int(lim)}",
        lambda kw, st, lim, pg: f"keyword: {_s(kw)}, sortType: 1, page: {int(pg)}, limit: {int(lim)}",
        lambda kw, st, lim, pg: f"keyword: {_s(kw)}, listType: 0, page: {int(pg)}, limit: {int(lim)}",
    )

    def _query_produtos(self, campos, keyword, sort_type, limit, page, variacao=0):
        args = self.VARIACOES[variacao](keyword, sort_type, limit, page)
        return f"{{ productOfferV2({args}) {{ nodes {{ {campos} }} pageInfo {{ page limit hasNextPage }} }} }}"

    def buscar_produtos(self, keyword: str, sort_type: int = 2, limit: int = 20, page: int = 1) -> list:
        todos = [(c, v) for v in range(len(self.VARIACOES)) for c in (CAMPOS_COMPLETOS, CAMPOS_MEDIOS, CAMPOS_MINIMOS)]
        combos = todos
        if self._campos is not None and self._variacao is not None:
            # começa pelo formato que já funcionou; se falhar, tenta os outros
            combos = [(self._campos, self._variacao)] + [x for x in todos if x != (self._campos, self._variacao)]
        ultimo = None
        for campos, v in combos:
            try:
                data = self._call(self._query_produtos(campos, keyword, sort_type, limit, page, v))
                self._campos, self._variacao = campos, v
                return data["productOfferV2"]["nodes"] or []
            except ShopeeAPIError as e:
                ultimo = e
                if e.code in (10020, 10030):  # senha errada / limite: não adianta variar
                    raise
        raise ultimo

    def link_curto(self, url: str, sub_id: str = "bot", prefixo: str = "") -> str:
        limpa = lambda t: "".join(c for c in t if c.isalnum())[:50]
        subs = [x for x in (limpa(prefixo), limpa(sub_id) or "bot") if x]
        lista = ", ".join(_s(x) for x in subs)
        q = f"mutation {{ generateShortLink(input: {{ originUrl: {_s(url)}, subIds: [{lista}] }}) {{ shortLink }} }}"
        return self._call(q)["generateShortLink"]["shortLink"]

    def diagnostico(self) -> list:
        """Testa consultas da mais simples à completa. Usado pelo 1_TESTAR."""
        testes = [("Consulta mínima", "{ productOfferV2(limit: 1) { nodes { productName } } }")]
        nomes = ["palavra+ordem+página", "palavra+página", "só palavra", "palavra+ordem 1", "palavra+listType"]
        for i, n in enumerate(nomes):
            testes.append((f"Busca ({n})", self._query_produtos("productName", "ssd", 2, 1, 1, i)))
        testes.append(("Campos completos", self._query_produtos(CAMPOS_COMPLETOS, "ssd", 2, 1, 1, 2)))
        resultado = []
        for nome, q in testes:
            try:
                self._call(q, tentativas=1)
                resultado.append((nome, True, ""))
            except Exception as e:
                resultado.append((nome, False, str(e)))
            time.sleep(1)
        return resultado
