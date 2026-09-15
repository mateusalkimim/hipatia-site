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

    index.html          o índice: a árvore desenhada, os passos e os cartões
    ver.html            o visor: barra com vizinhos nomeados, sumário, folha
                        atual, retomada e atalhos; o deck num quadro
    decks/<pasta>/      o HTML de cada deck e SÓ as figuras que ele referencia,
                        mais a PONTE (um script no fim) que conversa com o visor
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


def url_do_site():
    """O endereço do site no ar sai do remoto do git (owner/repo → Pages),
    não de uma string solta: se o repositório mudar de nome, o README e a
    tabela seguem sozinhos. `HS_URL_SITE` no ambiente sobrepõe."""
    fixo = os.environ.get("HS_URL_SITE")
    if fixo:
        return fixo.rstrip("/") + "/"
    try:
        import subprocess
        remoto = subprocess.run(["git", "-C", AQUI, "config", "--get", "remote.origin.url"],
                                capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return ""
    m = re.search(r"github\.com[:/]([^/]+)/([^/.]+?)(?:\.git)?$", remoto)
    if not m:
        return ""
    dono, repo = m.group(1), m.group(2)
    return f"https://{dono}.github.io/{repo}/"


URL_SITE = url_do_site()
AUTORIA = [
    ("Autor", "Mateus Felipe Alkimim Pereira"),
    ("Coautora", "Sara Catiele Nogueira Pereira"),
    ("Orientador", "Rosivaldo Antônio Gohnan"),
]

RE_REF = re.compile(r"""(src|href)=(["'])([^"']+)\2""")
RE_URL = re.compile(r"""url\((["']?)([^"')]+)\1\)""")
RE_TITLE = re.compile(r"<title>(.*?)</title>", re.S)
RE_TESE = re.compile(r'<p class="tese">(.*?)</p>', re.S)
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


# A PONTE: entra no fim de cada deck copiado. Os 17 decks compartilham o mesmo
# bloco de navegação (`slides`, `i`, `mostra(n)`, setas, clique nas metades,
# `#N` no hash), então uma ponte só serve a todos. Ela embrulha `mostra` para
# avisar o visor da folha atual, aceita "ir para a folha n" e teclas vindas
# de fora, e acrescenta o gesto de arrastar. Fora do visor ela não faz nada.
PONTE = r"""
<script>
(function () {
  if (window.parent === window || typeof mostra !== "function") return;
  var original = mostra;
  window.mostra = function (n) {
    var antes = i, ultimo = slides.length - 1;
    original(n);
    if (n > ultimo && antes === ultimo) parent.postMessage({hs: "fim"}, "*");
    else if (n < 0 && antes === 0) parent.postMessage({hs: "inicio"}, "*");
    parent.postMessage({hs: "folha", i: i, total: slides.length}, "*");
  };
  addEventListener("message", function (e) {
    var m = e.data;
    if (!m || !m.hs) return;
    if (m.hs === "ir") mostra(m.n);
    if (m.hs === "tecla") dispatchEvent(new KeyboardEvent("keydown", {key: m.key}));
  });
  var x0 = null;
  addEventListener("touchstart", function (e) { x0 = e.touches[0].clientX; }, {passive: true});
  addEventListener("touchend", function (e) {
    if (x0 === null) return;
    var dx = e.changedTouches[0].clientX - x0;
    if (Math.abs(dx) > 50) mostra(dx < 0 ? i + 1 : i - 1);
    x0 = null;
  });
  parent.postMessage({hs: "pronto", i: i, total: slides.length}, "*");
})();
</script>
"""


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

    if "</body>" not in texto:
        falha(f"{arq_html} não tem </body>; a ponte não tem onde entrar")
    texto = limpar_comentarios(texto)
    texto = texto.replace("</body>", PONTE + "</body>", 1)

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


def limpar_comentarios(texto):
    """Tira comentários de HTML e de CSS/JS da cópia derivada. Comentário é
    conversa da oficina, não conteúdo — e numa superfície pública ele conta
    como texto. A fonte fica intacta; só a cópia sai limpa."""
    texto = re.sub(r"<!--.*?-->", "", texto, flags=re.S)

    def limpa_bloco(m):
        return re.sub(r"/\*.*?\*/", "", m.group(0), flags=re.S)

    texto = re.sub(r"<style[^>]*>.*?</style>", limpa_bloco, texto, flags=re.S)
    texto = re.sub(r"<script(?![^>]*src=)[^>]*>.*?</script>", limpa_bloco, texto, flags=re.S)
    return re.sub(r"\n[ \t]*\n([ \t]*\n)+", "\n\n", texto)


def escrever_catalogo_readme(decks, raiz_saida):
    """A tabela do README entre <!-- catalogo:inicio --> e <!-- catalogo:fim -->
    é derivada: links para o visor, para o deck sozinho e para o PDF, no ar."""
    from urllib.parse import quote
    caminho = os.path.join(raiz_saida, "README.md")
    if not os.path.exists(caminho):
        return
    linhas = ["| # | seminário | abrir | PDF |", "|---|---|---|---|"]
    grupo_atual = None
    for d in decks:
        if d["grupo"] != grupo_atual:
            grupo_atual = d["grupo"]
            linhas.append(f"| | **{grupo_atual}** | | |")
        abrir = f"[visor]({URL_SITE}ver.html?d={quote(d['chave'])}) · [deck]({URL_SITE}{quote(d['caminho'])})"
        if d.get("variante"):
            abrir += (f" · [{d['variante']['rotulo']}]({URL_SITE}ver.html?d={quote(d['chave'])}"
                      f"&v={quote(d['variante']['codigo'])})")
        pdf = f"[PDF]({URL_SITE}{quote(d['pdf'])})" if d.get("pdf") else "—"
        nome = d["titulo"] + (" — " + d["sub"] if d["sub"] else "")
        linhas.append(f"| {d['chave']} | {nome} | {abrir} | {pdf} |")
    bloco = ("<!-- catalogo:inicio — gerado por gerar_site.py; não edite à mão -->\n"
             + "\n".join(linhas) + "\n<!-- catalogo:fim -->")
    texto = open(caminho, encoding="utf-8").read()
    novo, n = re.subn(r"<!-- catalogo:inicio.*?<!-- catalogo:fim -->", lambda m: bloco, texto, flags=re.S)
    if n != 1:
        falha("README.md sem o par de marcadores <!-- catalogo:inicio --> … <!-- catalogo:fim -->")
    # a seta de abrir, logo abaixo da introdução: no ar quando há endereço,
    # senão o index.html do clone
    if URL_SITE:
        seta = (f"**→ [Abrir as apresentações]({URL_SITE})**\n\n"
                "> **Estado: PROTÓTIPO.** No ar pelo GitHub Pages; também abre do clone,\n"
                "> sem servidor. Em aberto: a versão em inglês do índice e dos decks\n"
                "> (só o G3 a tem).")
    else:
        seta = ("**→ [Abrir as apresentações](index.html)**\n\n"
                "> **Estado: PROTÓTIPO.** Abre do clone, sem servidor; no GitHub o link\n"
                "> mostra só o arquivo.")
    bloco_seta = "<!-- site:inicio — gerado por gerar_site.py; não edite à mão -->\n" + seta + "\n<!-- site:fim -->"
    novo, n = re.subn(r"<!-- site:inicio.*?<!-- site:fim -->", lambda m: bloco_seta, novo, flags=re.S)
    if n != 1:
        falha("README.md sem o par de marcadores <!-- site:inicio --> … <!-- site:fim -->")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(novo)


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


# ---------------------------------------------------------------- estilo

# Tokens: o "Ítaca DS — tema claro" dos decks é o padrão; o escuro vem do
# itaca-ds/tokens.css. A medida de linha segue a norma de composição §2.1:
# 66 caracteres × 0,456 em ≈ 30em, em EM, nunca em ch.
CSS = r"""
:root {
  --bg: #f3f5f9; --card: #ffffff; --linha: #d9e0ec; --linha-forte: #c3cbd9;
  --ink: #16233f; --ink2: #3f4d6b; --muted: #7c88a1;
  --bronze: #a9713f; --bronze-fundo: #8f5e33; --bronze-soft: #c79b6e;
  --terracota: #b35430; --azul: #1e3a6b; --verde: #4e7a49;
  --sobre-ouro: #ffffff;
  --serif: Georgia, "Cormorant Garamond", "Times New Roman", serif;
  --sans: "Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --medida: 30em;
  color-scheme: light;
}
html[data-tema="escuro"] {
  --bg: #0a1424; --card: #111e34; --linha: #2a3d5e; --linha-forte: #3a5078;
  --ink: #f0e4cc; --ink2: #ded2ba; --muted: #8b98b3;
  --bronze: #c9a266; --bronze-fundo: #d4af6a; --bronze-soft: #b98f52;
  --terracota: #cf7550; --azul: #d4af6a; --verde: #7fa87a;
  --sobre-ouro: #0a1424;
  color-scheme: dark;
}
* { box-sizing: border-box; }
html { font-size: 17px; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font-family: var(--sans); line-height: 1.5;
}
a { color: var(--azul); }
:focus-visible { outline: 2px solid var(--bronze); outline-offset: 2px; }
.eyebrow {
  font-size: .72rem; letter-spacing: .22em; text-transform: uppercase;
  color: var(--bronze); font-weight: 600;
}
.botao {
  font: inherit; font-size: .85rem; cursor: pointer; line-height: 1.2;
  border: 1px solid var(--linha-forte); background: var(--card); color: var(--ink2);
  padding: .4rem .8rem; border-radius: .4rem; text-decoration: none;
  display: inline-flex; align-items: center; gap: .4rem;
}
.botao:hover { border-color: var(--bronze); color: var(--ink); }
.botao.pri { background: var(--bronze); border-color: var(--bronze); color: var(--sobre-ouro); font-weight: 600; }
.botao.pri:hover { background: var(--bronze-fundo); border-color: var(--bronze-fundo); }
.botao[aria-disabled="true"] { opacity: .4; pointer-events: none; }

/* o interruptor de tema: rótulo fixo, estado no aria-checked; visível sempre */
.tema {
  display: inline-flex; align-items: center; gap: .55rem; cursor: pointer;
  font: inherit; font-size: .85rem; color: var(--ink2); background: var(--card);
  border: 1px solid var(--linha-forte); border-radius: 2rem; padding: .3rem .75rem .3rem .5rem;
}
.tema:hover { border-color: var(--bronze); color: var(--ink); }
.tema .trilho {
  width: 2.3rem; height: 1.25rem; border-radius: 1rem; background: var(--linha-forte);
  position: relative; flex: none; transition: background .15s;
}
.tema .trilho::after {
  content: ""; position: absolute; top: .15rem; left: .15rem; width: .95rem; height: .95rem;
  border-radius: 50%; background: var(--card); transition: transform .15s;
  box-shadow: 0 1px 2px rgba(0,0,0,.25);
}
.tema[aria-checked="true"] .trilho { background: var(--bronze); }
.tema[aria-checked="true"] .trilho::after { transform: translateX(1.05rem); }
.tema svg { width: 1rem; height: 1rem; flex: none; }
.tema .sol { display: block; } .tema .lua { display: none; }
.tema[aria-checked="true"] .sol { display: none; } .tema[aria-checked="true"] .lua { display: block; }
"""

CSS_INDEX = r"""
body { padding-inline: clamp(16px, 4vw, 48px); padding-block: 0 4rem; }
.topo {
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
  padding-block: .9rem; border-bottom: 1px solid var(--linha); flex-wrap: wrap;
}
.cabeca { display: grid; grid-template-columns: minmax(0, 36rem) minmax(16rem, 24rem);
  gap: 2rem 3rem; align-items: start; padding-block: 2.2rem 1rem; }
h1 {
  font-family: var(--serif); font-weight: 500; font-size: clamp(2rem, 4.6vw, 3rem);
  line-height: 1.08; margin: .4rem 0 1rem; letter-spacing: -.01em;
}
h1 em { font-style: italic; color: var(--bronze); }
.tese {
  font-family: var(--serif); font-style: italic; font-size: 1.22rem;
  border-left: 3px solid var(--bronze); padding-left: 1rem; margin: 0 0 1rem;
  color: var(--ink2); max-width: var(--medida);
}
.prosa { max-width: var(--medida); color: var(--ink2); margin: .5rem 0; }
.comeco { display: flex; gap: .6rem; flex-wrap: wrap; align-items: center; margin-top: 1.2rem; }
.comeco .nota { color: var(--muted); font-size: .85rem; }
.grega {
  height: 8px; width: 96px; margin: 1.4rem 0 0;
  background: repeating-linear-gradient(90deg, var(--bronze) 0 8px, transparent 8px 16px);
}

/* a árvore desenhada — nó é caixa com o nome dentro; a linha pontilhada
   dourada é o caminho; legenda na mesma tela */
.arvore-fig { margin: 0; }
.arvore-fig svg { width: 100%; height: auto; max-height: 40vh; display: block; }
.arvore-fig a { text-decoration: none; }
.arvore-fig .no rect { fill: var(--card); stroke: var(--linha-forte); }
.arvore-fig a:hover .no rect, .arvore-fig a:focus-visible .no rect { stroke: var(--bronze); }
.arvore-fig .no text { fill: var(--ink); font-family: var(--serif); font-size: 15px; }
.arvore-fig .no .mini { fill: var(--muted); font-family: var(--sans); font-size: 10.5px; letter-spacing: .08em; }
.arvore-fig .caminho { stroke: var(--bronze); stroke-width: 1.5; stroke-dasharray: 2 4; fill: none; }
.arvore-fig .ponto { fill: var(--bronze); }
.arvore-fig figcaption { color: var(--muted); font-size: .8rem; margin-top: .4rem; }

.passos { list-style: none; padding: 0; margin: 1.6rem 0 0; display: grid; gap: .5rem; max-width: 40rem; }
.passos li { display: grid; grid-template-columns: 1.7rem 1fr; gap: .6rem; align-items: baseline; color: var(--ink2); }
.passos .n {
  width: 1.7rem; height: 1.7rem; border-radius: 50%; border: 1px solid var(--bronze);
  color: var(--bronze); font-size: .8rem; font-weight: 600; display: inline-grid; place-items: center;
}
.passos strong { color: var(--ink); font-weight: 600; }

h2 {
  font-family: var(--serif); font-weight: 500; font-size: 1.55rem;
  margin: 2.6rem 0 .2rem; line-height: 1.2; scroll-margin-top: 1rem;
}
h2 .num { color: var(--bronze); font-family: var(--sans); font-size: .75rem;
  letter-spacing: .22em; margin-right: .6rem; vertical-align: middle; }
.legenda { color: var(--muted); font-size: .9rem; margin: 0 0 1rem; max-width: var(--medida); }
.arcos { display: grid; grid-template-columns: 1fr 1fr; gap: 0 2.5rem; }
.arcos > section { min-width: 0; }
.grade { display: grid; grid-template-columns: repeat(auto-fill, minmax(15.5rem, 1fr)); gap: .9rem; }

/* cartão: o corpo inteiro é UM link; as ações secundárias ficam no pé */
.card {
  background: var(--card); border: 1px solid var(--linha); border-radius: .6rem;
  display: flex; flex-direction: column; min-width: 0; position: relative;
}
.card:hover, .card:focus-within { border-color: var(--bronze-soft); }
.card .capa { display: block; padding: .9rem 1rem .6rem; color: inherit; text-decoration: none; flex: 1; border-radius: .6rem .6rem 0 0; }
.card .chave {
  font-size: .72rem; letter-spacing: .12em; color: var(--bronze); font-weight: 600;
  display: flex; justify-content: space-between; align-items: baseline; gap: .5rem;
}
.card .chave .meta { color: var(--muted); font-weight: 400; letter-spacing: 0; text-transform: none; white-space: nowrap; }
.card h3 { font-family: var(--serif); font-weight: 500; font-size: 1.25rem; line-height: 1.18; margin: .3rem 0 .2rem; }
.card .sub { color: var(--ink2); font-size: .9rem; margin: 0; }
.card .estado { font-size: .78rem; color: var(--muted); margin-top: .5rem; min-height: 1.1em; }
.card.visto .estado::before { content: "aberto"; }
.card.concluido .estado::before { content: "✓ concluído"; color: var(--verde); }
.card.ultimo { border-color: var(--bronze); }
.card.ultimo .estado::before { content: "▶ continuar daqui"; color: var(--bronze); font-weight: 600; }
.card .pe {
  display: flex; gap: .3rem; flex-wrap: wrap; padding: .4rem .7rem .6rem;
  border-top: 1px solid var(--linha); font-size: .8rem;
}
.card .pe a { color: var(--ink2); text-decoration: none; padding: .2rem .5rem; border-radius: .3rem; }
.card .pe a:hover { color: var(--ink); background: var(--bg); }
.rodape {
  margin-top: 3.5rem; padding-top: 1.2rem; border-top: 1px solid var(--linha);
  color: var(--muted); font-size: .85rem; display: grid; gap: .3rem;
}
.rodape strong { color: var(--ink2); font-weight: 500; }
@media (max-width: 900px) {
  .cabeca { grid-template-columns: 1fr; }
  .arcos { grid-template-columns: 1fr; }
}
@media (max-width: 600px) { html { font-size: 16px; } }
"""

CSS_VISOR = r"""
html, body { height: 100%; }
body { display: grid; grid-template-rows: auto auto 1fr; grid-template-columns: auto 1fr; overflow: hidden; }
.barra {
  grid-column: 1 / -1; display: flex; align-items: center; gap: .5rem; padding: .35rem .7rem;
  border-bottom: 1px solid var(--linha); background: var(--card); font-size: .85rem;
  flex-wrap: wrap; min-height: 2.8rem;
}
.barra .grupo { display: flex; align-items: center; gap: .35rem; }
.barra .titulo {
  flex: 1 1 14rem; min-width: 8rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  font-family: var(--serif); font-size: 1.05rem; color: var(--ink);
}
.barra .titulo b { color: var(--bronze); font-family: var(--sans); font-size: .72rem;
  letter-spacing: .12em; margin-right: .5rem; font-weight: 600; }
.barra .posicao, .barra .folha { color: var(--muted); font-size: .8rem; white-space: nowrap; }
.barra .folha b { color: var(--ink); font-weight: 600; font-variant-numeric: tabular-nums; }
.barra .viz { max-width: 15rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: inline-block; }
.barra .viz .nome { color: var(--ink2); }
.barra .botao { padding: .3rem .6rem; }
.barra .botao.ico { padding: .3rem .5rem; font-weight: 600; }
.progresso { grid-column: 1 / -1; height: 3px; background: var(--linha); }
.progresso i { display: block; height: 100%; width: 0; background: var(--bronze); transition: width .2s; }

/* o sumário: visível em tela larga, gaveta em tela estreita */
.sumario {
  width: 17rem; overflow-y: auto; border-right: 1px solid var(--linha); background: var(--card);
  padding: .6rem 0 2rem; font-size: .85rem;
}
.sumario[hidden] { display: none; }
.sumario h2 { font-family: var(--sans); font-size: .72rem; letter-spacing: .22em; text-transform: uppercase;
  color: var(--muted); margin: .9rem .9rem .3rem; font-weight: 600; }
.sumario a { display: grid; grid-template-columns: 2rem 1fr auto; gap: .4rem; align-items: baseline;
  padding: .32rem .9rem; color: var(--ink2); text-decoration: none; }
.sumario a:hover { background: var(--bg); color: var(--ink); }
.sumario a b { color: var(--bronze); font-size: .72rem; letter-spacing: .1em; font-weight: 600; }
.sumario a .ok { color: var(--verde); font-size: .75rem; }
.sumario a.atual { background: var(--bg); color: var(--ink); box-shadow: inset 3px 0 0 var(--bronze); }
.palco { position: relative; min-width: 0; min-height: 0; display: flex; flex-direction: column; }
iframe { flex: 1; border: 0; width: 100%; height: 100%; background: #f3f5f9; }
.dica {
  position: absolute; left: 50%; bottom: 1.2rem; transform: translateX(-50%);
  background: var(--card); color: var(--ink2); border: 1px solid var(--linha-forte);
  border-radius: .5rem; padding: .5rem .9rem; font-size: .85rem; box-shadow: 0 6px 24px rgba(0,0,0,.18);
  display: flex; gap: .8rem; align-items: center; max-width: calc(100% - 2rem);
}
.dica[hidden] { display: none; }
.dica kbd { font: inherit; font-size: .8rem; border: 1px solid var(--linha-forte); border-radius: .25rem; padding: 0 .35rem; }
.dica button { font: inherit; font-size: .8rem; background: none; border: 0; color: var(--bronze); cursor: pointer; }
.veu { position: fixed; inset: 0; background: rgba(10,20,36,.55); display: grid; place-items: center; z-index: 10; }
.veu[hidden] { display: none; }
.caixa { background: var(--card); color: var(--ink); border-radius: .6rem; padding: 1.2rem 1.4rem; width: min(30rem, calc(100% - 2rem)); }
.caixa h2 { font-family: var(--serif); font-weight: 500; margin: 0 0 .6rem; font-size: 1.3rem; }
.caixa table { border-collapse: collapse; width: 100%; font-size: .9rem; }
.caixa td { padding: .3rem 0; border-bottom: 1px solid var(--linha); vertical-align: top; }
.caixa td:first-child { width: 11rem; }
.caixa kbd { font: inherit; font-size: .8rem; border: 1px solid var(--linha-forte); border-radius: .25rem; padding: 0 .35rem; margin-right: .2rem; }
.caixa .fechar { margin-top: .9rem; }
.aviso { padding: 2rem; }
@media (max-width: 1100px) {
  body { grid-template-columns: 1fr; }
  .sumario { position: fixed; top: 0; left: 0; bottom: 0; z-index: 9; box-shadow: 0 0 40px rgba(0,0,0,.3); }
}
@media (max-width: 760px) {
  .barra .viz .nome, .barra .posicao, .barra .tema .rotulo { display: none; }
  .barra .titulo { flex-basis: 100%; order: 9; font-size: .95rem; }
}
"""

# ------------------------------------------------------------------ script

JS_TEMA = r"""
(function () {
  var raiz = document.documentElement;
  function aplica(t) {
    if (t === 'escuro') raiz.setAttribute('data-tema', 'escuro');
    else raiz.removeAttribute('data-tema');
    document.querySelectorAll('.tema').forEach(function (b) {
      b.setAttribute('aria-checked', t === 'escuro' ? 'true' : 'false');
    });
  }
  // Claro é o padrão. Escuro só por escolha guardada — ou, sem escolha,
  // se a página já veio marcada (é o que permite testar o tema sem clique).
  var guardado = null;
  try { guardado = localStorage.getItem('hs-tema'); } catch (e) {}
  var inicial = guardado ? guardado : raiz.getAttribute('data-tema');
  inicial = inicial === 'escuro' ? 'escuro' : 'claro';
  aplica(inicial);
  document.addEventListener('DOMContentLoaded', function () {
    aplica(inicial);
    document.querySelectorAll('.tema').forEach(function (b) {
      b.addEventListener('click', function () {
        var novo = raiz.getAttribute('data-tema') === 'escuro' ? 'claro' : 'escuro';
        aplica(novo);
        try { localStorage.setItem('hs-tema', novo); } catch (e) {}
      });
    });
  });
})();
"""

# O que o navegador guarda sobre a leitura: quais decks foram abertos, quais
# chegaram à última folha, e onde a leitura parou. Melhor esforço: em file://
# alguns navegadores separam o armazenamento por pasta.
JS_LEITURA = r"""
var Leitura = {
  ler: function (k, padrao) { try { var v = localStorage.getItem(k); return v ? JSON.parse(v) : padrao; } catch (e) { return padrao; } },
  gravar: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} },
  vistos: function () { return this.ler('hs-vistos', {}); },
  marcar: function (chave, campo) { var v = this.vistos(); v[chave] = v[chave] || {}; v[chave][campo] = true; this.gravar('hs-vistos', v); },
  ultimo: function () { return this.ler('hs-ultimo', null); },
  parou: function (chave, folha) { this.gravar('hs-ultimo', {chave: chave, folha: folha}); }
};
"""

JS_INDEX = r"""
document.addEventListener('DOMContentLoaded', function () {
  var vistos = Leitura.vistos(), ultimo = Leitura.ultimo();
  document.querySelectorAll('.card').forEach(function (c) {
    var k = c.dataset.chave, v = vistos[k];
    if (v && v.aberto) c.classList.add('visto');
    if (v && v.concluido) c.classList.add('concluido');
  });
  var botao = document.getElementById('continuar'), nota = document.getElementById('continuar-nota');
  if (ultimo && ultimo.chave && document.getElementById('card-' + ultimo.chave)) {
    var card = document.getElementById('card-' + ultimo.chave);
    card.classList.add('ultimo');
    var nome = card.querySelector('h3').textContent;
    botao.textContent = 'Continuar: ' + ultimo.chave + ' · ' + nome;
    botao.href = 'ver.html?d=' + encodeURIComponent(ultimo.chave) + '&f=' + (ultimo.folha || 1);
    nota.textContent = 'folha ' + (ultimo.folha || 1) + ' — a leitura parou aqui';
  }
});
"""

JS_VISOR = r"""
(function () {
  var q = new URLSearchParams(location.search);
  var chave = q.get('d'), v = q.get('v'), f = q.get('f');
  var i = -1;
  for (var k = 0; k < CATALOGO.length; k++) if (CATALOGO[k].chave === chave) i = k;
  var quadro = document.getElementById('quadro');
  var titulo = document.getElementById('titulo');
  if (i < 0) {
    quadro.remove();
    titulo.textContent = 'Seminário não encontrado. Volte ao índice.';
    return;
  }
  var d = CATALOGO[i], total = d.folhas || 0, folhaAtual = 1, fimPedido = 0;
  var alvo = d.caminho, lang = d.lang;
  if (v && d.variante && d.variante.codigo === v) { alvo = d.variante.caminho; lang = d.variante.codigo; }
  document.title = d.chave + ' · ' + d.titulo;
  titulo.innerHTML = '<b></b>';
  titulo.firstChild.textContent = d.chave;
  titulo.appendChild(document.createTextNode(d.titulo + (d.sub ? ' — ' + d.sub : '')));
  document.getElementById('posicao').textContent = 'seminário ' + (i + 1) + ' de ' + CATALOGO.length;

  // folha inicial: ?f=N, ou ?f=fim (chegando pelo deck seguinte, de ré)
  var inicio = 1;
  if (f === 'fim') inicio = total || 1;
  else if (f && parseInt(f, 10) > 0) inicio = parseInt(f, 10);
  quadro.src = alvo + (inicio > 1 ? '#' + inicio : '');
  quadro.setAttribute('lang', lang);
  quadro.addEventListener('load', function () { try { quadro.contentWindow.focus(); } catch (e) {} });
  Leitura.marcar(d.chave, 'aberto');

  function liga(id, j, fim) {
    var a = document.getElementById(id);
    if (j < 0 || j >= CATALOGO.length) { a.setAttribute('aria-disabled', 'true'); a.querySelector('.nome').textContent = ''; return; }
    a.href = 'ver.html?d=' + encodeURIComponent(CATALOGO[j].chave) + (fim ? '&f=fim' : '');
    a.title = CATALOGO[j].chave + ' · ' + CATALOGO[j].titulo;
    a.querySelector('.chave').textContent = CATALOGO[j].chave;
    a.querySelector('.nome').textContent = ' · ' + CATALOGO[j].titulo;
  }
  liga('anterior', i - 1, true);
  liga('proximo', i + 1, false);
  var pdf = document.getElementById('pdf');
  if (d.pdf) pdf.href = d.pdf; else pdf.setAttribute('aria-disabled', 'true');
  var var_ = document.getElementById('variante');
  if (d.variante) {
    if (lang === d.variante.codigo) { var_.textContent = 'pt-BR'; var_.href = 'ver.html?d=' + encodeURIComponent(d.chave); }
    else { var_.textContent = d.variante.rotulo; var_.href = 'ver.html?d=' + encodeURIComponent(d.chave) + '&v=' + encodeURIComponent(d.variante.codigo); var_.setAttribute('lang', d.variante.codigo); }
  } else var_.remove();

  // sumário: aberto em tela larga, gaveta em tela estreita; a escolha fica guardada
  var sumario = document.getElementById('sumario'), botaoSum = document.getElementById('abrir-sumario');
  var vistos = Leitura.vistos();
  sumario.querySelectorAll('a[data-chave]').forEach(function (a) {
    var vv = vistos[a.dataset.chave];
    if (a.dataset.chave === d.chave) { a.classList.add('atual'); a.setAttribute('aria-current', 'page'); }
    if (vv && vv.concluido) a.querySelector('.ok').textContent = '✓';
  });
  var largo = window.matchMedia('(min-width: 1101px)').matches;
  var escolha = Leitura.ler('hs-sumario', null);
  var aberto = escolha === null ? largo : escolha;
  function mostraSumario(sim) {
    sumario.hidden = !sim; botaoSum.setAttribute('aria-expanded', sim ? 'true' : 'false');
  }
  mostraSumario(aberto);
  botaoSum.addEventListener('click', function () {
    aberto = sumario.hidden; mostraSumario(aberto); Leitura.gravar('hs-sumario', aberto);
  });
  if (!largo) sumario.addEventListener('click', function (e) { if (e.target.closest('a')) mostraSumario(false); });
  var atual = sumario.querySelector('a.atual'); if (atual) atual.scrollIntoView({block: 'center'});

  // a ponte: o deck avisa a folha; o visor mostra, guarda e responde
  var folhaEl = document.getElementById('folha'), barraProg = document.getElementById('progresso');
  var dica = document.getElementById('dica');
  function pintaFolha() {
    folhaEl.innerHTML = '<b></b>';
    folhaEl.firstChild.textContent = 'folha ' + folhaAtual;
    folhaEl.appendChild(document.createTextNode(' / ' + total));
    barraProg.style.width = total ? (100 * folhaAtual / total) + '%' : '0';
  }
  window.addEventListener('message', function (e) {
    var m = e.data; if (!m || !m.hs) return;
    if (m.hs === 'pronto' || m.hs === 'folha') {
      total = m.total; folhaAtual = m.i + 1; pintaFolha();
      Leitura.parou(d.chave, folhaAtual);
      if (folhaAtual === total) Leitura.marcar(d.chave, 'concluido');
      if (folhaAtual < total) fimPedido = 0;
    }
    if (m.hs === 'fim') {
      var prox = document.getElementById('proximo');
      if (prox.getAttribute('aria-disabled') === 'true') return;
      fimPedido++;
      if (fimPedido >= 2) { location.href = prox.href; return; }
      mostraDica('Fim deste seminário. Avance de novo para abrir o próximo: ' + prox.title, false);
    }
    if (m.hs === 'inicio') {
      var ant = document.getElementById('anterior');
      if (ant.getAttribute('aria-disabled') !== 'true') mostraDica('Início. O anterior é ' + ant.title + ' — use o botão ‹ na barra.', false);
    }
  });
  pintaFolha();

  // dica de primeira vez: uma linha, uma vez
  var dicaTexto = document.getElementById('dica-texto');
  function mostraDica(texto, primeira) {
    dicaTexto.textContent = texto; dica.hidden = false;
    clearTimeout(mostraDica.t); mostraDica.t = setTimeout(function () { dica.hidden = true; }, primeira ? 12000 : 5000);
  }
  document.getElementById('dica-fechar').addEventListener('click', function () { dica.hidden = true; Leitura.gravar('hs-dica', true); });
  if (!Leitura.ler('hs-dica', false)) { mostraDica('Setas ← → avançam as folhas. Tecle ? para ver todos os atalhos.', true); Leitura.gravar('hs-dica', true); }

  // atalhos do visor (a folha recebe as teclas quando o quadro tem foco;
  // quando o foco está na barra, o visor as encaminha)
  var veu = document.getElementById('atalhos');
  function abreAtalhos(sim) { veu.hidden = !sim; if (sim) veu.querySelector('button').focus(); else try { quadro.contentWindow.focus(); } catch (e) {} }
  document.getElementById('botao-atalhos').addEventListener('click', function () { abreAtalhos(true); });
  veu.querySelector('.fechar').addEventListener('click', function () { abreAtalhos(false); });
  veu.addEventListener('click', function (e) { if (e.target === veu) abreAtalhos(false); });
  document.getElementById('tela').addEventListener('click', function () {
    var el = document.documentElement;
    if (document.fullscreenElement) document.exitFullscreen(); else if (el.requestFullscreen) el.requestFullscreen();
  });
  var encaminha = ['ArrowRight', 'ArrowLeft', 'PageDown', 'PageUp', 'Home', 'End', ' '];
  document.addEventListener('keydown', function (e) {
    if (e.target && e.target.closest && e.target.closest('input, textarea')) return;
    if (e.key === '?') { abreAtalhos(veu.hidden); e.preventDefault(); return; }
    if (e.key === 'Escape') { if (!veu.hidden) abreAtalhos(false); return; }
    if (!veu.hidden) return;
    if (encaminha.indexOf(e.key) >= 0) { e.preventDefault(); try { quadro.contentWindow.postMessage({hs: 'tecla', key: e.key}, '*'); } catch (x) {} }
  });
})();
"""


# ------------------------------------------------------------------ páginas

def e(s):
    return html.escape(s, quote=True)


SVG_SOL = ('<svg class="sol" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">'
           '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>')
SVG_LUA = ('<svg class="lua" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">'
           '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></svg>')


def interruptor_tema():
    return (f'<button class="tema" type="button" role="switch" aria-checked="false">'
            f'{SVG_SOL}{SVG_LUA}<span class="trilho" aria-hidden="true"></span><span class="rotulo">Tema escuro</span></button>')


def card(d):
    meta = f"{d['folhas']} folhas" if d["folhas"] else "documento"
    sub = f'<p class="sub">{e(d["sub"])}</p>' if d["sub"] else ""
    pe = []
    if d.get("pdf"):
        pe.append(f'<a href="{e(d["pdf"])}">PDF</a>')
    if d.get("variante"):
        vv = d["variante"]
        pe.append(f'<a href="ver.html?d={e(d["chave"])}&v={e(vv["codigo"])}" lang="{e(vv["codigo"])}">{e(vv["rotulo"])}</a>')
    pe.append(f'<a href="{e(d["caminho"])}" title="abre o deck sozinho, sem o visor">só o deck</a>')
    return (f'<article class="card" id="card-{e(d["chave"])}" data-chave="{e(d["chave"])}">'
            f'<a class="capa" href="ver.html?d={e(d["chave"])}">'
            f'<div class="chave"><span>{e(d["chave"])}</span><span class="meta">{e(meta)}</span></div>'
            f'<h3>{e(d["titulo"])}</h3>{sub}<div class="estado"></div></a>'
            f'<div class="pe">{"".join(pe)}</div></article>')


def secao(ancora, numero, nome, legenda, decks):
    cards = "".join(card(d) for d in decks)
    return (f'<section id="{ancora}"><h2><span class="num">{e(numero)}</span>{e(nome)}</h2>'
            f'<p class="legenda">{e(legenda)}</p><div class="grade">{cards}</div></section>')


LEGENDAS = {
    "00": "O chão comum. Cada seminário aqui é pré-requisito dos dois arcos, e a ordem é a de conteúdo.",
    "10": "Geometria analítica e álgebra linear: o que uma transformação preserva.",
    "20": "Cálculo: o que acontece com uma função perto de um ponto.",
    "90": "Documentos que acompanham a série e não são aula.",
}


def figura_arvore(contagens):
    """A árvore, desenhada: três caixas ligadas pelo caminho pontilhado."""
    n0, n1, n2 = contagens
    return f"""<figure class="arvore-fig">
<svg viewBox="0 0 360 200" role="img" aria-label="A fundação alimenta dois arcos independentes: GAAL e Cálculo">
  <path class="caminho" d="M180 62 V 100 M180 100 H 90 V 122 M180 100 H 270 V 122"/>
  <circle class="ponto" cx="180" cy="100" r="3"/>
  <a href="#fundacao"><g class="no"><rect x="100" y="14" width="160" height="48" rx="6"/>
    <text x="112" y="34" class="mini">00 · {n0} SEMINÁRIOS</text><text x="112" y="53">a fundação</text></g></a>
  <a href="#gaal"><g class="no"><rect x="14" y="122" width="152" height="48" rx="6"/>
    <text x="26" y="142" class="mini">10 · {n1} SEMINÁRIOS</text><text x="26" y="161">arco GAAL</text></g></a>
  <a href="#calculo"><g class="no"><rect x="194" y="122" width="152" height="48" rx="6"/>
    <text x="206" y="142" class="mini">20 · {n2} SEMINÁRIOS</text><text x="206" y="161">arco do cálculo</text></g></a>
  <text x="180" y="192" class="mini" text-anchor="middle" style="fill: var(--muted); font-family: var(--sans); font-size: 10.5px">em qualquer ordem, um arco não depende do outro</text>
</svg>
<figcaption>A linha pontilhada é o caminho. Clique numa caixa para ir à lista.</figcaption>
</figure>"""


def gerar_index(decks, grupos, raiz_saida):
    por_grupo = {g: [d for d in decks if d["grupo"] == g] for g in grupos}

    def nome_grupo(g):
        num, _, resto = g.partition(" · ")
        return num, resto

    ancoras = ["fundacao", "gaal", "calculo", "extras"]
    partes = []
    n, nome = nome_grupo(grupos[0])
    partes.append(secao(ancoras[0], n, nome, LEGENDAS["00"], por_grupo[grupos[0]]))
    n1, nome1 = nome_grupo(grupos[1])
    n2, nome2 = nome_grupo(grupos[2])
    partes.append('<div class="arcos">'
                  + secao(ancoras[1], n1, nome1, LEGENDAS["10"], por_grupo[grupos[1]])
                  + secao(ancoras[2], n2, nome2, LEGENDAS["20"], por_grupo[grupos[2]])
                  + "</div>")
    n, nome = nome_grupo(grupos[3])
    partes.append(secao(ancoras[3], n, nome, LEGENDAS["90"], por_grupo[grupos[3]]))

    primeiro = por_grupo[grupos[0]][0]
    contagens = (len(por_grupo[grupos[0]]), len(por_grupo[grupos[1]]), len(por_grupo[grupos[2]]))
    autoria = "<br>".join(f"{e(p)} · <strong>{e(nome)}</strong>" for p, nome in AUTORIA)
    total = sum(d["folhas"] for d in decks)
    pagina = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(TITULO_SITE)}</title>
<style>{CSS}{CSS_INDEX}</style>
<script>{JS_TEMA}</script>
<script>{JS_LEITURA}</script>
<script>{JS_INDEX}</script>
</head>
<body>
<header class="topo">
  <div class="eyebrow">Apresentações · {len(decks)} seminários · {total} folhas</div>
  {interruptor_tema()}
</header>
<div class="cabeca">
  <div>
    <h1>Um curso de <em>visão computacional</em> e geometria da imagem</h1>
    <p class="tese">A série é uma árvore, não uma fila: a fundação alimenta os dois arcos, e os arcos não dependem um do outro.</p>
    <ol class="passos">
      <li><span class="n">1</span><span><strong>A fundação</strong>, do {e(primeiro["chave"])} ao {e(por_grupo[grupos[0]][-1]["chave"])}, na ordem.</span></li>
      <li><span class="n">2</span><span><strong>Um dos arcos</strong> — GAAL ou cálculo, em qualquer ordem; depois o outro.</span></li>
      <li><span class="n">3</span><span><strong>Os extras</strong> acompanham a série e não são aula.</span></li>
    </ol>
    <div class="comeco">
      <a class="botao pri" id="continuar" href="ver.html?d={e(primeiro["chave"])}">Começar pelo {e(primeiro["chave"])} · {e(primeiro["titulo"])}</a>
      <span class="nota" id="continuar-nota">o botão passa a lembrar onde a leitura parou</span>
    </div>
    <div class="grega"></div>
  </div>
  {figura_arvore(contagens)}
</div>
{"".join(partes)}
<footer class="rodape">
  <div>{autoria}</div>
  <div>Dentro de um seminário: setas, espaço ou <em>Page Down</em> avançam; <kbd>?</kbd> mostra os atalhos. O PDF é a mesma sequência, folha a folha.</div>
  <div>Código sob MIT; conteúdo dos seminários sob CC BY-SA 4.0, exceto as figuras de terceiros creditadas dentro de cada deck.</div>
  <div>Índice gerado em {date.today().isoformat()} por <code>gerar_site.py</code>. Não edite esta página: edite o deck de origem e gere de novo.</div>
</footer>
</body>
</html>
"""
    with open(os.path.join(raiz_saida, "index.html"), "w", encoding="utf-8") as f:
        f.write(pagina)


def sumario_html(decks, grupos):
    partes = []
    for g in grupos:
        num, _, nome = g.partition(" · ")
        itens = [d for d in decks if d["grupo"] == g]
        if not itens:
            continue
        links = "".join(
            f'<a href="ver.html?d={e(d["chave"])}" data-chave="{e(d["chave"])}"><b>{e(d["chave"])}</b>'
            f'<span>{e(d["titulo"])}</span><span class="ok"></span></a>' for d in itens)
        partes.append(f'<h2>{e(num)} · {e(nome)}</h2>{links}')
    return "".join(partes)


def gerar_visor(decks, grupos, raiz_saida):
    catalogo = [dict(chave=d["chave"], titulo=d["titulo"], sub=d["sub"], caminho=d["caminho"],
                     lang=d["lang"], pdf=d.get("pdf"), variante=d.get("variante"), folhas=d["folhas"])
                for d in decks]
    pagina = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(TITULO_SITE)}</title>
<style>{CSS}{CSS_VISOR}</style>
<script>{JS_TEMA}</script>
<script>{JS_LEITURA}</script>
<script>var CATALOGO = {json.dumps(catalogo, ensure_ascii=False)};</script>
</head>
<body>
<nav class="barra" aria-label="Navegação entre seminários">
  <div class="grupo">
    <a class="botao" href="index.html">← Índice</a>
    <button class="botao ico" id="abrir-sumario" type="button" aria-expanded="false" aria-controls="sumario" title="mostrar ou esconder o sumário">☰ Conteúdo</button>
  </div>
  <span class="posicao" id="posicao"></span>
  <span class="titulo" id="titulo"></span>
  <span class="folha" id="folha"></span>
  <div class="grupo">
    <a class="botao viz" id="anterior" href="#" rel="prev">‹ <span class="chave"></span><span class="nome"></span></a>
    <a class="botao viz" id="proximo" href="#" rel="next"><span class="chave"></span><span class="nome"></span> ›</a>
  </div>
  <div class="grupo">
    <a class="botao" id="variante" href="#"></a>
    <a class="botao" id="pdf" href="#">PDF</a>
    <button class="botao ico" id="tela" type="button" title="tela cheia">⛶</button>
    <button class="botao ico" id="botao-atalhos" type="button" title="atalhos do teclado" aria-haspopup="dialog">?</button>
    {interruptor_tema()}
  </div>
</nav>
<div class="progresso" aria-hidden="true"><i id="progresso"></i></div>
<aside class="sumario" id="sumario" aria-label="Sumário da série" hidden>{sumario_html(decks, grupos)}</aside>
<main class="palco">
  <iframe id="quadro" title="seminário" allow="fullscreen"></iframe>
  <div class="dica" id="dica" hidden><span id="dica-texto"></span><button type="button" id="dica-fechar">fechar</button></div>
</main>
<div class="veu" id="atalhos" role="dialog" aria-modal="true" aria-labelledby="atalhos-titulo" hidden>
  <div class="caixa">
    <h2 id="atalhos-titulo">Atalhos</h2>
    <table>
      <tr><td><kbd>→</kbd> <kbd>espaço</kbd> <kbd>Page Down</kbd></td><td>próxima folha</td></tr>
      <tr><td><kbd>←</kbd> <kbd>Page Up</kbd></td><td>folha anterior</td></tr>
      <tr><td><kbd>Home</kbd> / <kbd>End</kbd></td><td>primeira / última folha</td></tr>
      <tr><td><kbd>→</kbd> na última folha, duas vezes</td><td>abre o próximo seminário</td></tr>
      <tr><td>clique na metade direita / esquerda</td><td>avança / volta</td></tr>
      <tr><td>arrastar para o lado (toque)</td><td>avança / volta</td></tr>
      <tr><td><kbd>?</kbd></td><td>esta lista</td></tr>
      <tr><td><kbd>Esc</kbd></td><td>fecha esta lista</td></tr>
    </table>
    <button class="botao fechar" type="button">fechar</button>
  </div>
</div>
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
    gerar_visor(decks, grupos, raiz)
    escrever_catalogo_readme(decks, raiz)

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
