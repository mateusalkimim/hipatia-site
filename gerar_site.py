#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Monta o site das apresentações. Tudo que ele escreve é DERIVADO.

    python3 gerar_site.py                          # material no caminho padrão
    python3 gerar_site.py --material /caminho/hipatia/material
    python3 gerar_site.py --sem-pdf                # não copia os PDFs

O catálogo NÃO mora aqui. Ele é lido de `ferramentas/preparar_entrega.py`
(a lista ENTREGA: chave, pasta, html, pdf, grupo, nome) e de
`material/episodios.py` (que matérias cada deck ensina). Uma lista só, no
lugar onde ela já vivia — cópia divergiria em silêncio na primeira edição.

O que sai daqui:

    index.html          o índice, em árvore (fundação → dois arcos → extras)
    ver.html            o visor: um deck de cada vez, com barra e vizinhos
    decks/<pasta>/      o HTML de cada deck e SÓ as figuras que ele referencia
    vendor/tex-svg.js   uma cópia do MathJax para todos os decks
    pdf/                os PDFs com o nome de apresentação

Editar o gerado é o defeito: a próxima rodada apaga. Mexa no deck de origem
ou neste gerador. O gerador FALHA ALTO se alguma referência de um deck não
existir na saída — página com figura quebrada não entra.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import sys
from datetime import date

AQUI = os.path.dirname(os.path.abspath(__file__))
MATERIAL_PADRAO = "/mnt/b/AITools/interfaces/itaca-workspace/hipatia/material"

# Variantes de idioma declaradas fora do catálogo de entrega (que só conhece
# a versão em português, porque é ela que sobe ao projetor).
VARIANTES = {"G3": ("seminario-en.html", "en", "English version")}

TITULO_SITE = "Um curso de visão computacional e geometria da imagem"
AUTORIA = [
    ("Autor", "Mateus Felipe Alkimim Pereira"),
    ("Coautora", "Sara Catiele Nogueira Pereira"),
    ("Orientador", "Rosivaldo Antônio Gohnan"),
]

RE_REF = re.compile(r"""(src|href)=(["'])([^"']+)\2""")
RE_URL = re.compile(r"""url\((["']?)([^"')]+)\1\)""")
RE_TITLE = re.compile(r"<title>(.*?)</title>", re.S)
RE_TESE = re.compile(r'<p class="tese">(.*?)</p>', re.S)
RE_EYEBROW = re.compile(r'class="eyebrow">(.*?)</div>', re.S)
RE_TAG = re.compile(r"<[^>]+>")
RE_SLIDE = re.compile(r'<section class="slide')


def falha(msg):
    print("ERRO:", msg, file=sys.stderr)
    sys.exit(1)


def limpa(texto):
    return re.sub(r"\s+", " ", html.unescape(RE_TAG.sub("", texto))).strip()


def carregar_catalogo(material):
    ferramentas = os.path.join(os.path.dirname(material), "ferramentas")
    for p in (ferramentas, material):
        if not os.path.isdir(p):
            falha(f"pasta não existe: {p}")
        sys.path.insert(0, p)
    import preparar_entrega as pe  # noqa: E402
    import episodios as ep  # noqa: E402

    slug_para_id = {slug: i for i, slug in ep.PASTAS.items()}
    itens = []
    for chave, pasta, arq_html, arq_pdf, grupo, nome_final in pe.ENTREGA:
        eid = slug_para_id.get(pasta)
        materias = ep.EPISODIOS[eid][1] if eid in ep.EPISODIOS else []
        itens.append(dict(chave=chave, pasta=pasta, html=arq_html, pdf=arq_pdf,
                          grupo=grupo, nome_final=nome_final, materias=materias))
    grupos = [pe.GRUPO_BASE, pe.GRUPO_GAAL, pe.GRUPO_CALC, pe.GRUPO_EXTRA]
    return itens, grupos


def refs_do_html(texto):
    achadas = []
    for m in RE_REF.finditer(texto):
        achadas.append(m.group(3))
    for m in RE_URL.finditer(texto):
        achadas.append(m.group(2))
    saida = []
    for r in achadas:
        r0 = r.strip()
        if not r0 or r0.startswith(("#", "data:", "http:", "https:", "mailto:", "javascript:", "//")):
            continue
        if "." not in os.path.basename(r0.split("?")[0].split("#")[0]):
            continue
        saida.append(r0)
    return sorted(set(saida))


def sha_arquivo(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def copiar(origem, destino):
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    if os.path.exists(destino) and sha_arquivo(destino) != sha_arquivo(origem):
        falha(f"colisão de nome com conteúdo diferente: {destino}")
    if not os.path.exists(destino):
        shutil.copy2(origem, destino)


def levar_deck(material, item, arq_html, raiz_saida):
    """Copia um HTML e o que ele referencia. Devolve o dicionário do deck."""
    pasta_origem = os.path.join(material, item["pasta"])
    origem = os.path.join(pasta_origem, arq_html)
    if not os.path.exists(origem):
        falha(f"deck não existe: {origem}")
    texto = open(origem, encoding="utf-8").read()
    pasta_saida = os.path.join(raiz_saida, "decks", item["pasta"])
    os.makedirs(pasta_saida, exist_ok=True)

    trocas = {}
    for ref in refs_do_html(texto):
        alvo = os.path.normpath(os.path.join(pasta_origem, ref))
        if not os.path.exists(alvo):
            falha(f"{item['pasta']}/{arq_html} referencia o que não existe: {ref}")
        if os.path.basename(alvo) == "tex-svg.js":
            copiar(alvo, os.path.join(raiz_saida, "vendor", "tex-svg.js"))
            trocas[ref] = "../../vendor/tex-svg.js"
        elif os.path.commonpath([alvo, pasta_origem]) == pasta_origem:
            rel = os.path.relpath(alvo, pasta_origem)
            copiar(alvo, os.path.join(pasta_saida, rel))
        else:
            nome = os.path.basename(alvo)
            copiar(alvo, os.path.join(pasta_saida, "externas", nome))
            trocas[ref] = "externas/" + nome

    for velho, novo in trocas.items():
        n = 0
        for q in ('"', "'"):
            texto, k = re.subn(re.escape(q + velho + q), q + novo + q, texto)
            n += k
        texto, k = re.subn(r"url\(" + re.escape(velho) + r"\)", "url(" + novo + ")", texto)
        n += k
        if n == 0:
            falha(f"não consegui reescrever a referência {velho} em {arq_html}")

    with open(os.path.join(pasta_saida, arq_html), "w", encoding="utf-8") as f:
        f.write(texto)

    m = RE_TITLE.search(texto)
    titulo_cheio = limpa(m.group(1)) if m else arq_html
    if " — " in titulo_cheio:
        titulo, sub = titulo_cheio.split(" — ", 1)
    else:
        titulo, sub = titulo_cheio, ""
    m = RE_TESE.search(texto)
    tese = limpa(m.group(1)) if m else ""
    lang = "en" if 'lang="en' in texto[:300] else "pt-BR"
    return dict(caminho=f"decks/{item['pasta']}/{arq_html}", titulo=titulo, sub=sub,
                tese=tese, folhas=len(RE_SLIDE.findall(texto)), lang=lang)


def conferir_saida(raiz_saida):
    """Toda referência de todo HTML gerado tem de existir. Sem exceção."""
    faltando = []
    for pasta, _, arquivos in os.walk(os.path.join(raiz_saida, "decks")):
        for a in arquivos:
            if not a.endswith(".html"):
                continue
            texto = open(os.path.join(pasta, a), encoding="utf-8").read()
            for ref in refs_do_html(texto):
                if not os.path.exists(os.path.normpath(os.path.join(pasta, ref))):
                    faltando.append(f"{os.path.relpath(pasta, raiz_saida)}/{a} → {ref}")
    return faltando


# ---------------------------------------------------------------- páginas

CSS = r"""
:root {
  --bg: #f3f5f9; --card: #ffffff; --linha: #d9e0ec;
  --ink: #16233f; --ink2: #3f4d6b; --muted: #7c88a1;
  --bronze: #a9713f; --bronze-fundo: #8f5e33; --bronze-soft: #c79b6e;
  --terracota: #b35430; --azul: #1e3a6b;
  --serif: Georgia, "Cormorant Garamond", "Times New Roman", serif;
  --sans: "Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --medida: 34em;
  color-scheme: light;
}
html[data-tema="escuro"] {
  --bg: #0a1424; --card: #111e34; --linha: #2a3d5e;
  --ink: #f0e4cc; --ink2: #ded2ba; --muted: #8b98b3;
  --bronze: #c9a266; --bronze-fundo: #d4af6a; --bronze-soft: #b98f52;
  --terracota: #cf7550; --azul: #d4af6a;
  color-scheme: dark;
}
* { box-sizing: border-box; }
html { font-size: 17px; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font-family: var(--sans); line-height: 1.5;
  padding-inline: clamp(16px, 4vw, 48px); padding-block: 0 4rem;
}
a { color: var(--azul); }
.topo {
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
  padding-block: 1rem; border-bottom: 1px solid var(--linha); flex-wrap: wrap;
}
.eyebrow {
  font-size: .78rem; letter-spacing: .12em; text-transform: uppercase;
  color: var(--bronze); font-weight: 600;
}
.botao {
  font: inherit; font-size: .85rem; cursor: pointer;
  border: 1px solid var(--linha); background: var(--card); color: var(--ink2);
  padding: .35rem .8rem; border-radius: .4rem;
}
.botao:hover { border-color: var(--bronze); color: var(--ink); }
.cabeca { max-width: 46em; padding-block: 2.5rem 1.5rem; }
h1 {
  font-family: var(--serif); font-weight: 500; font-size: clamp(2rem, 5vw, 3.2rem);
  line-height: 1.08; margin: .4rem 0 1rem; letter-spacing: -.01em;
}
h1 em { font-style: italic; color: var(--bronze); }
.tese {
  font-family: var(--serif); font-style: italic; font-size: 1.25rem;
  border-left: 3px solid var(--bronze); padding-left: 1rem; margin: 0 0 1rem;
  color: var(--ink2); max-width: var(--medida);
}
.prosa { max-width: var(--medida); color: var(--ink2); margin: .5rem 0; }
.grega {
  height: 8px; width: 96px; margin: 1.2rem 0;
  background: repeating-linear-gradient(90deg, var(--bronze) 0 8px, transparent 8px 16px);
}
h2 {
  font-family: var(--serif); font-weight: 500; font-size: 1.55rem;
  margin: 2.6rem 0 .2rem; line-height: 1.2;
}
h2 .num { color: var(--bronze); font-family: var(--sans); font-size: .8rem;
  letter-spacing: .12em; margin-right: .6rem; vertical-align: middle; }
.legenda { color: var(--muted); font-size: .9rem; margin: 0 0 1rem; max-width: var(--medida); }
.arvore { display: grid; grid-template-columns: 1fr 1fr; gap: 0 2.5rem; }
.arvore > section { min-width: 0; }
.tronco { position: relative; }
.tronco::after {
  content: ""; display: block; height: 2.2rem; width: 2px; margin: .4rem auto 0;
  background: linear-gradient(var(--bronze), transparent);
}
.grade { display: grid; grid-template-columns: repeat(auto-fill, minmax(17rem, 1fr)); gap: 1rem; }
.card {
  background: var(--card); border: 1px solid var(--linha); border-radius: .6rem;
  padding: 1rem 1.1rem 1rem; display: flex; flex-direction: column; gap: .45rem;
  min-width: 0;
}
.card:hover { border-color: var(--bronze-soft); }
.chave {
  font-size: .75rem; letter-spacing: .1em; color: var(--bronze); font-weight: 600;
  display: flex; justify-content: space-between; align-items: baseline;
}
.chave .meta { color: var(--muted); font-weight: 400; letter-spacing: 0; text-transform: none; }
.card h3 {
  font-family: var(--serif); font-weight: 500; font-size: 1.28rem; line-height: 1.18; margin: 0;
}
.card .sub { color: var(--ink2); font-size: .92rem; margin: 0; }
.card .tese {
  font-size: .95rem; margin: .2rem 0 .3rem; padding-left: .7rem; border-width: 2px;
  display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden;
}
.acoes { margin-top: auto; display: flex; gap: .5rem; flex-wrap: wrap; padding-top: .4rem; }
.acoes a {
  text-decoration: none; font-size: .85rem; padding: .35rem .8rem; border-radius: .4rem;
  border: 1px solid var(--linha); color: var(--ink2);
}
.acoes a.abrir { background: var(--bronze); border-color: var(--bronze); color: #fff; }
html[data-tema="escuro"] .acoes a.abrir { color: #0a1424; }
.acoes a:hover { border-color: var(--bronze); }
.rodape {
  margin-top: 3.5rem; padding-top: 1.2rem; border-top: 1px solid var(--linha);
  color: var(--muted); font-size: .85rem; display: grid; gap: .3rem;
}
.rodape strong { color: var(--ink2); font-weight: 500; }
@media (max-width: 760px) {
  .arvore { grid-template-columns: 1fr; }
  html { font-size: 16px; }
}
"""

JS_TEMA = r"""
(function () {
  var raiz = document.documentElement;
  function aplica(t) {
    if (t === 'escuro') raiz.setAttribute('data-tema', 'escuro');
    else raiz.removeAttribute('data-tema');
    var b = document.getElementById('tema');
    if (b) b.textContent = t === 'escuro' ? 'tema claro' : 'tema escuro';
  }
  // Claro é o padrão. Escuro só por escolha guardada — ou, sem escolha,
  // se a página já veio marcada (é o que permite testar o tema sem clique).
  var guardado = null;
  try { guardado = localStorage.getItem('hs-tema'); } catch (e) {}
  var inicial = guardado ? guardado : raiz.getAttribute('data-tema');
  inicial = inicial === 'escuro' ? 'escuro' : 'claro';
  aplica(inicial);
  document.addEventListener('DOMContentLoaded', function () {
    var b = document.getElementById('tema');
    if (!b) return;
    aplica(inicial);
    b.addEventListener('click', function () {
      var novo = raiz.getAttribute('data-tema') === 'escuro' ? 'claro' : 'escuro';
      aplica(novo);
      try { localStorage.setItem('hs-tema', novo); } catch (e) {}
    });
  });
})();
"""


def e(s):
    return html.escape(s, quote=True)


def card(d):
    meta = f"{d['folhas']} folhas" if d["folhas"] else "documento"
    n = len(d["materias"])
    if n:
        meta += f" · {n} {'matéria' if n == 1 else 'matérias'} do mapa"
    acoes = [f'<a class="abrir" href="ver.html?d={e(d["chave"])}">Abrir</a>']
    if d.get("pdf"):
        acoes.append(f'<a href="{e(d["pdf"])}">PDF</a>')
    if d.get("variante"):
        v = d["variante"]
        acoes.append(f'<a href="ver.html?d={e(d["chave"])}&v={e(v["codigo"])}" lang="{e(v["codigo"])}">{e(v["rotulo"])}</a>')
    tese = f'<p class="tese">{e(d["tese"])}</p>' if d["tese"] else ""
    sub = f'<p class="sub">{e(d["sub"])}</p>' if d["sub"] else ""
    return (f'<article class="card" id="{e(d["chave"])}">'
            f'<div class="chave"><span>{e(d["chave"])}</span><span class="meta">{e(meta)}</span></div>'
            f'<h3>{e(d["titulo"])}</h3>{sub}{tese}'
            f'<div class="acoes">{"".join(acoes)}</div></article>')


def secao(numero, nome, legenda, decks, classe=""):
    cards = "".join(card(d) for d in decks)
    return (f'<section class="{classe}"><h2><span class="num">{e(numero)}</span>{e(nome)}</h2>'
            f'<p class="legenda">{e(legenda)}</p><div class="grade">{cards}</div></section>')


LEGENDAS = {
    "00": "O chão comum. Cada seminário aqui é pré-requisito dos dois arcos, e a ordem é a de conteúdo.",
    "10": "Geometria analítica e álgebra linear: o que uma transformação preserva.",
    "20": "Cálculo: o que acontece com uma função perto de um ponto.",
    "90": "Documentos que acompanham a série e não são aula.",
}


def gerar_index(decks, grupos, raiz_saida):
    por_grupo = {g: [d for d in decks if d["grupo"] == g] for g in grupos}

    def nome_grupo(g):
        num, _, resto = g.partition(" · ")
        return num, resto

    partes = []
    n, nome = nome_grupo(grupos[0])
    partes.append(secao(n, nome, LEGENDAS["00"], por_grupo[grupos[0]], "tronco"))
    n1, nome1 = nome_grupo(grupos[1])
    n2, nome2 = nome_grupo(grupos[2])
    partes.append('<div class="arvore">'
                  + secao(n1, nome1, LEGENDAS["10"], por_grupo[grupos[1]])
                  + secao(n2, nome2, LEGENDAS["20"], por_grupo[grupos[2]])
                  + "</div>")
    n, nome = nome_grupo(grupos[3])
    partes.append(secao(n, nome, LEGENDAS["90"], por_grupo[grupos[3]]))

    autoria = "<br>".join(f"{e(p)} · <strong>{e(nome)}</strong>" for p, nome in AUTORIA)
    total = sum(d["folhas"] for d in decks)
    pagina = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(TITULO_SITE)}</title>
<style>{CSS}</style>
<script>{JS_TEMA}</script>
</head>
<body>
<header class="topo">
  <div class="eyebrow">Apresentações · {len(decks)} seminários · {total} folhas</div>
  <button class="botao" id="tema" type="button">tema escuro</button>
</header>
<div class="cabeca">
  <h1>Um curso de <em>visão computacional</em> e geometria da imagem</h1>
  <p class="tese">A série é uma árvore, não uma fila: a fundação alimenta os dois arcos, e os arcos não dependem um do outro.</p>
  <p class="prosa">Abra um seminário e avance com as setas do teclado, espaço ou <em>Page Down</em>. Cada deck é uma página inteira em 16:9; o PDF é a mesma sequência, folha a folha, para o tablet e o projetor.</p>
  <div class="grega"></div>
</div>
{"".join(partes)}
<footer class="rodape">
  <div>{autoria}</div>
  <div>Código sob MIT; conteúdo dos seminários sob CC BY-SA 4.0, exceto as figuras de terceiros creditadas dentro de cada deck.</div>
  <div>Índice gerado em {date.today().isoformat()} por <code>gerar_site.py</code>. Não edite esta página: edite o deck de origem e gere de novo.</div>
</footer>
</body>
</html>
"""
    with open(os.path.join(raiz_saida, "index.html"), "w", encoding="utf-8") as f:
        f.write(pagina)


CSS_VISOR = r"""
html, body { height: 100%; }
body { padding: 0; display: flex; flex-direction: column; overflow: hidden; }
.barra {
  display: flex; align-items: center; gap: .6rem; padding: .35rem .8rem;
  border-bottom: 1px solid var(--linha); background: var(--card); font-size: .85rem;
  flex-wrap: wrap; min-height: 2.6rem;
}
.barra a { text-decoration: none; color: var(--ink2); padding: .25rem .55rem;
  border: 1px solid transparent; border-radius: .35rem; white-space: nowrap; }
.barra a:hover { border-color: var(--linha); color: var(--ink); }
.barra a[aria-disabled="true"] { opacity: .35; pointer-events: none; }
.barra .titulo { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap; font-family: var(--serif); font-size: 1.05rem; }
.barra .titulo b { color: var(--bronze); font-family: var(--sans); font-size: .75rem;
  letter-spacing: .1em; margin-right: .5rem; font-weight: 600; }
.barra .botao { padding: .25rem .6rem; }
iframe { flex: 1; border: 0; width: 100%; background: #f3f5f9; }
.aviso { padding: 2rem; }
"""

JS_VISOR = r"""
(function () {
  var q = new URLSearchParams(location.search);
  var chave = q.get('d'), v = q.get('v');
  var i = -1;
  for (var k = 0; k < CATALOGO.length; k++) if (CATALOGO[k].chave === chave) i = k;
  var quadro = document.getElementById('quadro');
  var titulo = document.getElementById('titulo');
  if (i < 0) {
    quadro.remove();
    titulo.textContent = 'Seminário não encontrado. Volte ao índice.';
    return;
  }
  var d = CATALOGO[i];
  var alvo = d.caminho, lang = d.lang;
  if (v && d.variante && d.variante.codigo === v) { alvo = d.variante.caminho; lang = d.variante.codigo; }
  document.title = d.chave + ' · ' + d.titulo;
  titulo.innerHTML = '<b></b>';
  titulo.firstChild.textContent = d.chave;
  titulo.appendChild(document.createTextNode(d.titulo + (d.sub ? ' — ' + d.sub : '')));
  quadro.src = alvo;
  quadro.setAttribute('lang', lang);
  quadro.addEventListener('load', function () { try { quadro.contentWindow.focus(); } catch (e) {} });
  function liga(id, j) {
    var a = document.getElementById(id);
    if (j < 0 || j >= CATALOGO.length) { a.setAttribute('aria-disabled', 'true'); return; }
    a.href = 'ver.html?d=' + encodeURIComponent(CATALOGO[j].chave);
    a.title = CATALOGO[j].chave + ' · ' + CATALOGO[j].titulo;
  }
  liga('anterior', i - 1);
  liga('proximo', i + 1);
  var pdf = document.getElementById('pdf');
  if (d.pdf) pdf.href = d.pdf; else pdf.setAttribute('aria-disabled', 'true');
  var var_ = document.getElementById('variante');
  if (d.variante) {
    if (lang === d.variante.codigo) {
      var_.textContent = 'pt-BR';
      var_.href = 'ver.html?d=' + encodeURIComponent(d.chave);
    } else {
      var_.textContent = d.variante.rotulo;
      var_.href = 'ver.html?d=' + encodeURIComponent(d.chave) + '&v=' + encodeURIComponent(d.variante.codigo);
      var_.setAttribute('lang', d.variante.codigo);
    }
  } else var_.remove();
})();
"""


def gerar_visor(decks, raiz_saida):
    catalogo = [dict(chave=d["chave"], titulo=d["titulo"], sub=d["sub"], caminho=d["caminho"],
                     lang=d["lang"], pdf=d.get("pdf"), variante=d.get("variante"))
                for d in decks]
    pagina = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(TITULO_SITE)}</title>
<style>{CSS}{CSS_VISOR}</style>
<script>{JS_TEMA}</script>
<script>var CATALOGO = {json.dumps(catalogo, ensure_ascii=False)};</script>
</head>
<body>
<nav class="barra">
  <a href="index.html">← Índice</a>
  <span class="titulo" id="titulo"></span>
  <a id="variante" href="#"></a>
  <a id="pdf" href="#">PDF</a>
  <a id="anterior" href="#" title="seminário anterior">‹ anterior</a>
  <a id="proximo" href="#" title="próximo seminário">próximo ›</a>
  <button class="botao" id="tema" type="button">tema escuro</button>
</nav>
<iframe id="quadro" title="seminário" allowfullscreen></iframe>
<script>{JS_VISOR}</script>
</body>
</html>
"""
    with open(os.path.join(raiz_saida, "ver.html"), "w", encoding="utf-8") as f:
        f.write(pagina)


# ------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--material", default=os.environ.get("HIPATIA_MATERIAL", MATERIAL_PADRAO))
    ap.add_argument("--sem-pdf", action="store_true")
    ap.add_argument("--saida", default=AQUI)
    args = ap.parse_args()

    material = os.path.abspath(args.material)
    raiz = os.path.abspath(args.saida)
    itens, grupos = carregar_catalogo(material)

    for gerado in ("decks", "vendor", "pdf"):
        alvo = os.path.join(raiz, gerado)
        if os.path.isdir(alvo):
            shutil.rmtree(alvo)

    decks = []
    for item in itens:
        d = levar_deck(material, item, item["html"], raiz)
        d.update(chave=item["chave"], grupo=item["grupo"], materias=item["materias"])
        # O nome do cartão é o nome de apresentação do catálogo (o mesmo do
        # PDF que sobe ao projetor), não o <title> do deck, que inverte a
        # ordem em alguns. O subtítulo do <title> entra quando o nome não tem.
        nome = re.sub(r"\.pdf$", "", item["nome_final"])
        prefixo, sep, resto = nome.partition(" · ")
        if sep and prefixo == item["chave"]:
            nome = resto
        if " — " in nome:
            d["titulo"], d["sub"] = nome.split(" — ", 1)
        else:
            d["titulo"] = nome
        if item["chave"] in VARIANTES:
            arq, codigo, rotulo = VARIANTES[item["chave"]]
            dv = levar_deck(material, item, arq, raiz)
            d["variante"] = dict(codigo=codigo, rotulo=rotulo, caminho=dv["caminho"])
        if not args.sem_pdf:
            pdf_origem = os.path.join(material, item["pasta"], item["pdf"])
            html_origem = os.path.join(material, item["pasta"], item["html"])
            if os.path.exists(pdf_origem):
                if os.path.getmtime(pdf_origem) < os.path.getmtime(html_origem):
                    print(f"  aviso: PDF mais velho que o HTML em {item['chave']} — regerar na origem")
                copiar(pdf_origem, os.path.join(raiz, "pdf", item["nome_final"]))
                d["pdf"] = "pdf/" + item["nome_final"]
            else:
                print(f"  aviso: sem PDF para {item['chave']} ({item['pdf']})")
        decks.append(d)
        extra = " + " + VARIANTES[item["chave"]][1] if item["chave"] in VARIANTES else ""
        print(f"  {item['chave']:>4}  {d['folhas']:>3} folhas  {d['titulo']}{extra}")

    gerar_index(decks, grupos, raiz)
    gerar_visor(decks, raiz)

    faltando = conferir_saida(raiz)
    if faltando:
        for f in faltando:
            print("  FALTA:", f)
        falha(f"{len(faltando)} referência(s) sem arquivo na saída")

    total = 0
    for pasta, _, arquivos in os.walk(os.path.join(raiz, "decks")):
        total += sum(os.path.getsize(os.path.join(pasta, a)) for a in arquivos)
    print(f"\n{len(decks)} seminários · decks/ com {total / 1e6:.1f} MB · nenhuma referência quebrada")


if __name__ == "__main__":
    main()
