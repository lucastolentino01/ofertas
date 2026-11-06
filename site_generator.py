"""Gera a página de ofertas (docs/index.html) publicada grátis no GitHub Pages."""
import html
import json
from datetime import datetime, timedelta, timezone

BRT = timezone(timedelta(hours=-3))


def gerar_site(ofertas: list, destino, titulo: str = "Tech Barato BR", canal_link: str = "") -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    dados = json.dumps([{k: o.get(k) for k in
                         ("nome", "preco", "preco_original", "desconto", "imagem", "nota", "vendas", "link", "categoria")}
                        for o in ofertas], ensure_ascii=False).replace("</", "<\\/")
    atualizado = datetime.now(BRT).strftime("%d/%m/%Y às %H:%M")
    t = html.escape(titulo)
    botao_canal = (f'<a class="canal" href="{html.escape(canal_link)}" target="_blank" rel="noopener">'
                   f'📢 Entrar no canal de ofertas</a>') if canal_link else ""
    pagina = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{t} — ofertas da Shopee</title>
<meta name="description" content="Ofertas selecionadas da Shopee com desconto, atualizadas automaticamente.">
<style>
:root{{--bg:#f6f6f4;--card:#fff;--txt:#1b1b1b;--sub:#6b6b6b;--acc:#ee4d2d;--line:#e6e4df}}
@media(prefers-color-scheme:dark){{:root{{--bg:#121212;--card:#1d1d1d;--txt:#f1f1f1;--sub:#a3a3a3;--line:#2c2c2c}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--txt);font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}
header{{padding:28px 16px 12px;max-width:1100px;margin:auto}}
h1{{margin:0;font-size:28px;letter-spacing:-.02em}}h1 span{{color:var(--acc)}}
.sub{{color:var(--sub);margin:6px 0 14px}}
.canal{{display:inline-block;background:var(--acc);color:#fff;padding:10px 16px;border-radius:10px;text-decoration:none;font-weight:600}}
.filtros{{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}}
.filtros button{{border:1px solid var(--line);background:var(--card);color:var(--txt);padding:6px 12px;border-radius:999px;cursor:pointer;font:inherit}}
.filtros button.on{{background:var(--txt);color:var(--bg);border-color:var(--txt)}}
main{{max-width:1100px;margin:auto;padding:8px 16px 40px;display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:14px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column}}
.card img{{width:100%;aspect-ratio:1;object-fit:cover;background:#ddd}}
.info{{padding:12px;display:flex;flex-direction:column;gap:4px;flex:1}}
.nome{{font-size:14px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
.de{{color:var(--sub);text-decoration:line-through;font-size:13px}}
.por{{font-size:20px;font-weight:700}}
.tag{{align-self:flex-start;background:var(--acc);color:#fff;font-size:12px;font-weight:700;padding:2px 8px;border-radius:6px}}
.meta{{color:var(--sub);font-size:12px}}
.btn{{margin-top:auto;text-align:center;background:var(--acc);color:#fff;text-decoration:none;padding:10px;border-radius:10px;font-weight:600}}
footer{{text-align:center;color:var(--sub);font-size:12px;padding:0 16px 30px}}
</style></head><body>
<header><h1>{t} <span>●</span></h1>
<p class="sub">Ofertas da Shopee escolhidas a dedo · atualizado em {atualizado}</p>
{botao_canal}<div class="filtros" id="f"></div></header>
<main id="g"></main>
<footer>Como afiliado da Shopee, posso receber comissão pelas compras feitas pelos links, sem custo extra para você. Preços e estoque podem mudar.</footer>
<script>
const D={dados};
const brl=v=>v.toLocaleString('pt-BR',{{style:'currency',currency:'BRL'}});
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]));
let cat='Todas';
function render(){{
 const g=document.getElementById('g');
 const L=D.filter(o=>cat==='Todas'||o.categoria===cat);
 g.innerHTML=L.length?L.map(o=>`<article class="card"><img loading="lazy" src="${{esc(o.imagem)}}" alt="">
 <div class="info">${{o.desconto?`<span class="tag">${{o.desconto}}% OFF</span>`:''}}
 <div class="nome">${{esc(o.nome)}}</div>
 ${{o.preco_original&&o.preco_original>o.preco?`<div class="de">${{brl(o.preco_original)}}</div>`:''}}
 <div class="por">${{brl(o.preco)}}</div>
 <div class="meta">${{o.nota?'⭐ '+o.nota.toFixed(1):''}} ${{o.vendas?'· '+o.vendas+' vendidos':''}}</div>
 <a class="btn" href="${{esc(o.link)}}" target="_blank" rel="nofollow sponsored noopener">Ver na Shopee</a></div></article>`).join('')
 :'<p>Nenhuma oferta ainda — volte em breve!</p>';
 const cats=['Todas',...new Set(D.map(o=>o.categoria))];
 document.getElementById('f').innerHTML=cats.length>2?cats.map(c=>`<button class="${{c===cat?'on':''}}" data-c="${{esc(c)}}">${{esc(c)}}</button>`).join(''):'';
}}
document.getElementById('f').onclick=e=>{{if(e.target.dataset.c){{cat=e.target.dataset.c;render()}}}};
render();
</script></body></html>"""
    destino.write_text(pagina, encoding="utf-8")
