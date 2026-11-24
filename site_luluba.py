"""Site da Luluba Store (docs/index.html): vitrine no visual da marca.

Chamado pelo site_generator.gerar_site quando THEME=luluba.
Recursos: capa com botões do Telegram e Instagram, faixa de Natal (nov/dez),
achadinho do dia, busca, categorias amigáveis, ordenação e selo da Shein.
"""
import html
import json
import os
from datetime import datetime, timedelta, timezone

BRT = timezone(timedelta(hours=-3))


def gerar_site_luluba(ofertas, destino, titulo="Luluba Store", canal_link=""):
    destino.parent.mkdir(parents=True, exist_ok=True)
    campos = ("nome", "preco", "preco_original", "desconto", "imagem", "nota", "vendas",
              "link", "categoria", "loja", "postado_em")
    dados = json.dumps([{k: o.get(k) for k in campos} for o in ofertas],
                       ensure_ascii=False).replace("</", "<\\/")
    agora = datetime.now(BRT)
    atualizado = agora.strftime("%d/%m às %H:%M")
    natal = agora.month in (11, 12)
    canal = html.escape(canal_link or "https://t.me/lulubastore")
    insta = html.escape("https://instagram.com/" + os.getenv("IG_HANDLE", "@luluba.store").lstrip("@"))
    t = html.escape(titulo)

    faixa_natal = """<div class="natal"><span>🎄</span><div><b>Especial de Natal</b>
<small>decoração, pisca-pisca, roupas e presentes com preço baixo</small></div>
<button data-g="Natal">Ver achadinhos</button></div>""" if natal else ""

    pagina = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{t} · achadinhos com preço baixo</title>
<meta name="description" content="Achadinhos de moda feminina, infantil e casa com desconto, garimpados todos os dias.">
<meta property="og:title" content="{t} · achadinhos com preço baixo">
<meta property="og:description" content="Moda feminina, infantil e casa com desconto, atualizado todo dia.">
<meta name="theme-color" content="#C2697A">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,600;0,700;1,600&family=Poppins:wght@400;500;600;700&display=swap">
<style>
:root{{--bg:#FBF5F1;--bg2:#F3E3DB;--card:#fff;--txt:#2B1F22;--sub:#86707a;--rose:#C2697A;--deep:#9E4A5C;
--line:#EEDFD7;--gold:#C9A15A;--green:#2F5D45;--red:#A8323E;--sh:0 6px 22px rgba(122,52,66,.08)}}
@media(prefers-color-scheme:dark){{:root{{--bg:#1d1517;--bg2:#2a1e21;--card:#271d20;--txt:#f7efea;--sub:#c4adb2;--line:#3a2c30;--sh:none}}}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}
body{{margin:0;background:var(--bg);color:var(--txt);font:15px/1.5 Poppins,system-ui,sans-serif;-webkit-font-smoothing:antialiased}}
a{{color:inherit}}
.wrap{{max-width:1120px;margin:auto;padding:0 16px}}
/* capa */
.hero{{background:radial-gradient(900px 500px at 85% -10%,var(--bg2),transparent 70%);padding:34px 0 22px}}
.top{{display:flex;align-items:center;justify-content:space-between;gap:12px}}
.logo{{font:italic 600 34px/1 Lora,serif;color:var(--deep);letter-spacing:-.5px;text-decoration:none}}
@media(prefers-color-scheme:dark){{.logo{{color:#e9a8b5}}}}
.att{{font-size:12px;color:var(--sub);background:var(--card);border:1px solid var(--line);padding:6px 12px;border-radius:99px;white-space:nowrap}}
.att i{{display:inline-block;width:7px;height:7px;border-radius:50%;background:#3bb273;margin-right:6px;vertical-align:1px}}
h1{{font:700 clamp(30px,6vw,52px)/1.05 Lora,serif;letter-spacing:-1px;margin:26px 0 10px;max-width:15ch}}
h1 em{{color:var(--rose);font-style:italic}}
.lead{{color:var(--sub);margin:0 0 20px;max-width:46ch;font-size:16px}}
.cta{{display:flex;gap:10px;flex-wrap:wrap}}
.b{{display:inline-flex;align-items:center;gap:8px;padding:12px 18px;border-radius:14px;font-weight:600;text-decoration:none;transition:transform .15s}}
.b:hover{{transform:translateY(-2px)}}
.b1{{background:var(--rose);color:#fff;box-shadow:0 8px 20px rgba(194,105,122,.35)}}
.b2{{background:var(--card);border:1px solid var(--line);color:var(--txt)}}
.b svg{{width:18px;height:18px}}
/* natal */
.natal{{margin:22px 0 0;display:flex;align-items:center;gap:14px;padding:14px 16px;border-radius:18px;color:#fff;
background:linear-gradient(110deg,var(--red),#7A1F2B 55%,var(--green));box-shadow:var(--sh)}}
.natal span{{font-size:30px}}.natal div{{flex:1;line-height:1.3}}.natal small{{display:block;opacity:.85;font-size:13px}}
.natal button{{border:0;background:#fff;color:var(--red);font:600 13px Poppins;padding:9px 14px;border-radius:10px;cursor:pointer;white-space:nowrap}}
/* destaque */
.dest{{margin:22px 0 4px;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.1fr);gap:0;background:var(--card);border:1px solid var(--line);
border-radius:22px;overflow:hidden;box-shadow:var(--sh)}}
.dest .im{{position:relative;background:#f1e6e0;min-height:260px}}
.dest img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
.dest .tx{{padding:24px;display:flex;flex-direction:column;gap:8px;justify-content:center}}
.kick{{font:600 12px Poppins;letter-spacing:2px;color:var(--rose);text-transform:uppercase}}
.dest h2{{font:700 24px/1.2 Lora,serif;margin:0}}
@media(max-width:640px){{.dest{{grid-template-columns:1fr}}.dest .im{{min-height:240px}}}}
/* barra */
.bar{{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--bg) 92%,transparent);backdrop-filter:blur(8px);
border-bottom:1px solid var(--line);padding:12px 0;margin-top:22px}}
.bar .wrap{{display:flex;flex-direction:column;gap:10px}}
.row{{display:flex;gap:10px}}
.busca{{flex:1;display:flex;align-items:center;gap:8px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:0 12px}}
.busca input{{border:0;outline:0;background:transparent;color:var(--txt);font:inherit;padding:10px 0;width:100%}}
select{{border:1px solid var(--line);background:var(--card);color:var(--txt);border-radius:12px;padding:0 10px;font:inherit;font-size:14px}}
.chips{{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;padding-bottom:2px}}.chips::-webkit-scrollbar{{display:none}}
.chips button{{flex:none;border:1px solid var(--line);background:var(--card);color:var(--txt);padding:7px 14px;border-radius:99px;
cursor:pointer;font:500 14px Poppins}}
.chips button.on{{background:var(--txt);color:var(--bg);border-color:var(--txt)}}
.chips b{{font-weight:500;opacity:.55;margin-left:4px;font-size:12px}}
/* grade */
.info-l{{color:var(--sub);font-size:13px;margin:16px 0 10px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(178px,1fr));gap:14px;padding-bottom:30px}}
@media(max-width:420px){{.grid{{grid-template-columns:1fr 1fr;gap:10px}}}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:18px;overflow:hidden;display:flex;flex-direction:column;
box-shadow:var(--sh);transition:transform .15s,box-shadow .15s;text-decoration:none}}
.card:hover{{transform:translateY(-3px);box-shadow:0 12px 30px rgba(122,52,66,.14)}}
.ph{{position:relative;aspect-ratio:1;background:#f1e6e0}}
.ph img{{position:absolute;inset:0;z-index:1;width:100%;height:100%;object-fit:cover;display:block}}
.ph .vazio{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font:italic 600 26px Lora;color:#d3b3ab}}
.off{{position:absolute;z-index:2;top:10px;left:10px;background:var(--rose);color:#fff;font:700 12px Poppins;padding:4px 9px;border-radius:99px}}
.shein{{position:absolute;z-index:2;top:10px;right:10px;background:#111;color:#fff;font:700 11px Poppins;letter-spacing:1px;padding:4px 8px;border-radius:6px}}
.novo{{position:absolute;z-index:2;bottom:10px;left:10px;background:#fff;color:var(--deep);font:600 11px Poppins;padding:3px 8px;border-radius:99px}}
.in{{padding:12px;display:flex;flex-direction:column;gap:3px;flex:1}}
.nm{{font-size:13.5px;line-height:1.35;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:2.7em}}
.de{{color:var(--sub);text-decoration:line-through;font-size:12.5px;margin-top:4px}}
.pr{{font:700 21px/1.1 Lora,serif;color:var(--rose)}}
.mt{{color:var(--sub);font-size:12px}}
.go{{margin-top:auto;padding-top:10px}}
.go span{{display:block;text-align:center;background:var(--rose);color:#fff;padding:9px;border-radius:11px;font-weight:600;font-size:13.5px}}
.vazio-l{{grid-column:1/-1;text-align:center;color:var(--sub);padding:40px 0}}
.mais[hidden]{{display:none}}.mais{{display:block;margin:0 auto 34px;border:1px solid var(--line);background:var(--card);color:var(--txt);padding:11px 22px;border-radius:12px;font:600 14px Poppins;cursor:pointer}}
/* rodapé */
.tg{{background:var(--deep);color:#fff;border-radius:22px;padding:26px;display:flex;align-items:center;gap:18px;flex-wrap:wrap;margin-bottom:28px}}
.tg div{{flex:1;min-width:220px}}.tg h3{{font:700 24px Lora,serif;margin:0 0 4px}}.tg p{{margin:0;opacity:.85}}
.tg a{{background:#fff;color:var(--deep);padding:12px 18px;border-radius:12px;font-weight:700;text-decoration:none}}
footer{{color:var(--sub);font-size:12px;text-align:center;padding:0 16px 34px;line-height:1.6}}
</style></head><body>
<section class="hero"><div class="wrap">
 <div class="top"><a class="logo" href="#">Luluba</a><span class="att"><i></i>atualizado {atualizado}</span></div>
 <h1>Achadinhos lindos com <em>preço baixo</em></h1>
 <p class="lead">Moda feminina, infantil e casa garimpados todos os dias na Shopee e na Shein. É só tocar e comprar.</p>
 <div class="cta">
  <a class="b b1" href="{canal}" target="_blank" rel="noopener"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M9.8 15.2 9.6 19c.4 0 .6-.2.8-.4l2-1.9 4.1 3c.8.4 1.3.2 1.5-.7l2.7-12.7c.3-1.1-.4-1.6-1.1-1.3L3.5 10.8c-1.1.4-1.1 1-.2 1.3l4.1 1.3 9.5-6c.4-.3.9-.1.6.2z"/></svg>Ofertas no Telegram</a>
  <a class="b b2" href="{insta}" target="_blank" rel="noopener"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor"/></svg>@luluba.store</a>
 </div>
 {faixa_natal}
 <div id="dest"></div>
</div></section>
<div class="bar"><div class="wrap">
 <div class="row"><label class="busca"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
 <input id="q" type="search" placeholder="Buscar vestido, pijama, pisca-pisca..."></label>
 <select id="ord" aria-label="Ordenar"><option value="novo">Mais novos</option><option value="desc">Maior desconto</option><option value="barato">Menor preço</option><option value="vendas">Mais vendidos</option></select></div>
 <div class="chips" id="chips"></div>
</div></div>
<main class="wrap"><p class="info-l" id="cont"></p><div class="grid" id="g"></div><button class="mais" id="mais" hidden>Ver mais achadinhos</button>
<section class="tg"><div><h3>Não perca nenhuma oferta 💌</h3><p>No canal do Telegram eu posto achadinhos novos o dia todo. É grátis!</p></div>
<a href="{canal}" target="_blank" rel="noopener">Entrar no canal</a></section></main>
<footer>Como afiliada da Shopee e da Shein, a Luluba pode receber comissão pelas compras feitas pelos links, sem custo extra para você.<br>Preços e estoque podem mudar a qualquer momento.</footer>
<script>
const D={dados};
const G=[['Natal',/natal|pisca|guirlanda|presepio|presépio|enfeite|arvore|árvore|festao|festão|papai noel|caneca|bola de natal|meia natal/i],
['Infantil',/infantil|menina|bebe|bebê|crian/i],
['Casa',/decora|quadro|vaso|luminar|almofada|espelho|organiz|toalha|mesa posta|casa/i],
['Beleza',/maquiagem|skincare|escova|batom|perfume|beleza/i],
['Acessórios',/bolsa|brinco|colar|sandalia|sandália|bijuteria|acess/i]];
const grupo=o=>{{const s=(o.categoria||'')+' '+(o.nome||'');for(const[n,r]of G)if(r.test(s))return n;return'Moda'}};
D.forEach(o=>{{o.g=grupo(o);o.t=Date.parse(o.postado_em||'')||0}});
const brl=v=>Number(v||0).toLocaleString('pt-BR',{{style:'currency',currency:'BRL'}});
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const agora=Date.now();
function card(o){{
 const img=o.imagem?`<img loading="lazy" src="${{esc(o.imagem)}}" alt="${{esc(o.nome)}}" onerror="this.remove()">`:'';
 return `<a class="card" href="${{esc(o.link)}}" target="_blank" rel="nofollow sponsored noopener">
 <div class="ph"><span class="vazio">Luluba</span>${{img}}${{o.desconto?`<span class="off">-${{o.desconto}}%</span>`:''}}
 ${{o.loja==='Shein'?'<span class="shein">SHEIN</span>':''}}${{o.t&&agora-o.t<6*36e5?'<span class="novo">novo</span>':''}}</div>
 <div class="in"><div class="nm">${{esc(o.nome)}}</div>
 ${{o.preco_original&&o.preco_original>o.preco?`<div class="de">${{brl(o.preco_original)}}</div>`:'<div class="de" style="visibility:hidden">.</div>'}}
 <div class="pr">${{brl(o.preco)}}</div>
 <div class="mt">${{o.nota?'★ '+Number(o.nota).toFixed(1):''}}${{o.vendas?(o.nota?' · ':'')+Number(o.vendas).toLocaleString('pt-BR')+' vendidos':''}}</div>
 <div class="go"><span>Quero o meu</span></div></div></a>`}}
// achadinho do dia
const dd=[...D].filter(o=>o.imagem).sort((a,b)=>(b.desconto||0)-(a.desconto||0)||(b.vendas||0)-(a.vendas||0))[0];
if(dd)document.getElementById('dest').innerHTML=`<div class="dest"><div class="im"><img src="${{esc(dd.imagem)}}" alt=""></div>
<div class="tx"><span class="kick">✨ Achadinho do dia</span><h2>${{esc(dd.nome)}}</h2>
${{dd.preco_original&&dd.preco_original>dd.preco?`<div class="de">${{brl(dd.preco_original)}}</div>`:''}}
<div class="pr" style="font-size:34px">${{brl(dd.preco)}}${{dd.desconto?` <span style="font:700 14px Poppins;background:var(--rose);color:#fff;padding:4px 10px;border-radius:99px;vertical-align:6px">-${{dd.desconto}}%</span>`:''}}</div>
<a class="b b1" style="align-self:flex-start;margin-top:6px" href="${{esc(dd.link)}}" target="_blank" rel="nofollow sponsored noopener">Quero o meu</a></div></div>`;
let cat='Tudo',q='',ord='novo',lim=24;
const ordem=['Tudo','Natal','Moda','Infantil','Casa','Beleza','Acessórios','Shein'];
function chips(){{
 const n={{Tudo:D.length,Shein:D.filter(o=>o.loja==='Shein').length}};D.forEach(o=>n[o.g]=(n[o.g]||0)+1);
 document.getElementById('chips').innerHTML=ordem.filter(c=>n[c]).map(c=>`<button class="${{c===cat?'on':''}}" data-c="${{c}}">${{c==='Natal'?'🎄 ':''}}${{c}}<b>${{n[c]}}</b></button>`).join('')}}
function render(){{
 const s=q.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();
 let L=D.filter(o=>(cat==='Tudo'||(cat==='Shein'?o.loja==='Shein':o.g===cat))&&(!s||o.nome.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase().includes(s)));
 const f={{novo:(a,b)=>b.t-a.t,desc:(a,b)=>(b.desconto||0)-(a.desconto||0),barato:(a,b)=>a.preco-b.preco,vendas:(a,b)=>(b.vendas||0)-(a.vendas||0)}}[ord];
 L.sort(f);
 document.getElementById('cont').textContent=L.length?`${{L.length}} achadinho${{L.length>1?'s':''}}${{cat!=='Tudo'?' em '+cat:''}}`:'';
 document.getElementById('g').innerHTML=L.length?L.slice(0,lim).map(card).join(''):'<p class="vazio-l">Nada por aqui ainda. Volte mais tarde ou entre no canal do Telegram 💕</p>';
 document.getElementById('mais').hidden=L.length<=lim;chips()}}
document.getElementById('chips').onclick=e=>{{const b=e.target.closest('button');if(b){{cat=b.dataset.c;lim=24;render()}}}};
document.getElementById('q').oninput=e=>{{q=e.target.value;lim=24;render()}};
document.getElementById('ord').onchange=e=>{{ord=e.target.value;render()}};
document.getElementById('mais').onclick=()=>{{lim+=24;render()}};
document.querySelectorAll('[data-g]').forEach(b=>b.onclick=()=>{{cat=b.dataset.g;render();document.querySelector('.bar').scrollIntoView()}});
render();
</script></body></html>"""
    destino.write_text(pagina, encoding="utf-8")
