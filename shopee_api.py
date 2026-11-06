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
        self._campos = None  # descobre sozinho qual conjunto de campos funciona

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
            if code == 10030 and tentativa < tentativas - 1:  # limite de requisições
                time.sleep(2 ** (tentativa + 1))
                continue
            raise ShopeeAPIError(f"Erro da API Shopee ({code}): {msg}", code)
        raise ShopeeAPIError("Falha após várias tentativas")

    def _query_produtos(self, campos, keyword, sort_type, limit, page):
        args = f"keyword: {_s(keyword)}, sortType: {int(sort_type)}, page: {int(page)}, limit: {int(limit)}"
        return f"{{ productOfferV2({args}) {{ nodes {{ {campos} }} pageInfo {{ page limit hasNextPage }} }} }}"

    def buscar_produtos(self, keyword: str, sort_type: int = 2, limit: int = 20, page: int = 1) -> list:
        opcoes = [self._campos] if self._campos else [CAMPOS_COMPLETOS, CAMPOS_MEDIOS, CAMPOS_MINIMOS]
        ultimo = None
        for campos in opcoes:
            try:
                data = self._call(self._query_produtos(campos, keyword, sort_type, limit, page))
                self._campos = campos
                return data["productOfferV2"]["nodes"] or []
            except ShopeeAPIError as e:
                ultimo = e
                if e.code in (10020, 10030):  # senha errada / limite: não adianta trocar campos
                    raise
        raise ultimo

    def link_curto(self, url: str, sub_id: str = "bot") -> str:
        sub = "".join(c for c in sub_id if c.isalnum())[:50] or "bot"
        q = f"mutation {{ generateShortLink(input: {{ originUrl: {_s(url)}, subIds: [{_s(sub)}] }}) {{ shortLink }} }}"
        return self._call(q)["generateShortLink"]["shortLink"]

    def diagnostico(self) -> list:
        """Testa consultas da mais simples à completa. Usado pelo 1_TESTAR."""
        testes = [
            ("Consulta mínima", "{ productOfferV2(limit: 1) { nodes { productName } } }"),
            ("Busca por palavra", self._query_produtos("productName", "ssd", 2, 1, 1)),
            ("Campos mínimos", self._query_produtos(CAMPOS_MINIMOS, "ssd", 2, 1, 1)),
            ("Campos médios", self._query_produtos(CAMPOS_MEDIOS, "ssd", 2, 1, 1)),
            ("Campos completos", self._query_produtos(CAMPOS_COMPLETOS, "ssd", 2, 1, 1)),
        ]
        resultado = []
        for nome, q in testes:
            try:
                self._call(q, tentativas=1)
                resultado.append((nome, True, ""))
            except Exception as e:
                resultado.append((nome, False, str(e)))
            time.sleep(1)
        return resultado
