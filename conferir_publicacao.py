#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Confere se um texto publicado carrega vocabulario que nao e do leitor.

Existe por causa de um defeito medido: uma pagina publicada deste conjunto de
repositorios trazia, nas duas linguas, quatro paragrafos sobre o processo de
producao -- numeros de uma triagem, vocabulario de revisao interna -- e
afirmava, com link, que outro repositorio do mesmo autor continha uma
afirmacao falsa ainda publicada.

As outras verificacoes estavam todas em verde: citacao, idioma, layout,
geometria, interatividade. Nenhuma delas responde "este texto e do leitor?".
Um paragrafo pode estar correto, bem-composto, bem-traduzido e com citacao
conferida contra o livro, e ainda assim nao pertencer aquela superficie.

    python3 conferir_publicacao.py              # confere o repositorio
    python3 conferir_publicacao.py --controle   # o controle negativo E o positivo
    python3 conferir_publicacao.py --estrito    # aviso tambem reprova
    python3 conferir_publicacao.py --commits 5  # inclui as N ultimas mensagens

Superficie publica inclui comentario de codigo e mensagem de commit: um
repositorio publicado nao tem gaveta.

As copias nos repositorios sao derivadas de uma fonte unica -- corrigir na
fonte e redistribuir, nunca na copia: copia editada vira segundo original, e
diverge em silencio na primeira correcao.

Excecoes: `publicacao-excecoes.txt`, uma por linha, `<sha10> | <motivo>`. O sha
sai impresso ao lado de cada achado. Excecao sem motivo nao vale, e ela fica
presa ao trecho: mudou o texto, mudou o sha, e a excecao caduca. Nao ha
excecao por categoria inteira, de proposito.
"""
from __future__ import annotations

import argparse
import hashlib
import html as _html
import io
import json
import os
import re
import subprocess
import sys
import tokenize

AQUI = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------
# O LEXICO (norma-de-publicacao.md §2)
#
# Cada entrada e (categoria, regex, o que e). Vai EMBUTIDO de proposito: quem
# clona o repositorio roda o portao sem a maquina de quem o escreveu.
#
# O que NAO entra, e por que:
#   · "gate"/"gates" em ingles -- e PORTA LOGICA em metade destes
#     repositorios. Acusar isso e o defeito da sonda que acusa o certo;
#   · "proposta"/"proposal" soltas -- palavra comum. So a EXPRESSAO do rito;
#   · "operador"/"operator" sozinhos -- e operador MATEMATICO. So a forma
#     definida, e ainda assim com desambiguacao adiante.
# --------------------------------------------------------------------------
LEXICO = [
    # -- papeis da casa -----------------------------------------------------
    # A forma contraida ("d" + "o papel") nao casava em `\bo <papel>\b`: o "o"
    # colado no "d" nao tem fronteira de palavra antes. Duas notas de producao
    # ficaram publicadas dentro do CSS de uma pagina por causa disso.
    ("papel", r"\b(?:o|do|ao|pelo|no|meu) operador\b"
              r"(?!\s+(?:linear|diferencial|adjunto|identidade|de deriva))",
     "papel da casa (se for operador matematico, declare a excecao)"),
    ("papel", r"\bthe operator\b(?!\s+(?:that|which|is|acts|takes|maps|\w+\s+operator))",
     "papel da casa (se for operador matematico, declare a excecao)"),
    ("papel", r"\b(?:esta|nesta|desta|da nossa)\s+casa\b", "'a casa' e nome interno"),
    ("papel", r"\bthis house\b", "'this house' e nome interno"),

    # -- componentes de Itaca ----------------------------------------------
    ("componente", r"\b(?:Ítaca|Itaca)\b", "nome do sistema"),
    ("componente", r"\bOdysseus\b", "componente interno"),
    ("componente", r"\bDelfos\b", "componente interno"),
    ("componente", r"\b(?:Têmis|Temis)\b", "componente interno"),
    ("componente", r"\b(?:Hipátia|Hipatia)\b", "componente interno"),
    ("componente", r"\bMouseion\b", "componente interno"),
    ("componente", r"\b(?:Limín|Limin)\b", "componente interno"),
    ("componente", r"\bPharo\b", "componente interno"),
    ("componente", r"\b(?:Pítia|Pitia)\b", "componente interno"),
    ("componente", r"\b(?:Asclépio|Asclepio)\b", "componente interno"),

    # -- vocabulario de rito ------------------------------------------------
    ("rito", r"\bport(?:ão|ao)(?:es|ões)?\b", "'portao' e vocabulario de rito"),
    ("rito", r"\bmesa cega\b|\bblind table\b", "rito de julgamento"),
    ("rito", r"\bratifica(?:ção|cao|do|da|dos|das|r)\b|\bratifi(?:ed|cation)\b",
     "rito de ratificacao"),
    ("rito", r"\b(?:em|como|marcad[oa]s? como)\s+proposta\b|\bmarked as proposal\b",
     "estado do rito"),
    ("rito", r"\baguarda(?:m)?\s+ratifica|\bawait(?:s|ing)?\s+ratifi", "rito"),
    ("rito", r"\[N[0-3]\]\s", "nivel de acao do registro interno"),
    ("rito", r"\bjob no Delfos\b|\bcheckpoint da sess(?:ão|ao)\b", "rito"),

    # -- infraestrutura e modelos locais ------------------------------------
    ("infra", r"\bphi-4\b", "modelo local"),
    ("infra", r"\bQwen[\w.-]*\b", "modelo local"),
    ("infra", r"\bbge-m3\b", "modelo local"),
    ("infra", r"\bChromaDB\b|\bfastembed\b", "infra local"),
    ("infra", r"\bvLLM\b", "infra local"),
    ("infra", r"/mnt/[a-z]/|~/\.itaca|~/venvs/", "caminho de maquina"),
    ("infra", r"\bWSL2?\b", "infra local"),

    # -- numeros de processo -------------------------------------------------
    ("processo", r"\b\d+\s+propostos?\b|\b\d+\s+proposed\b", "numero de rodada"),
    ("processo", r"\b\d+\s+passaram\b|\b\d+\s+passed\b", "numero de rodada"),
    ("processo", r"\bna primeira rodada\b|\bin the first round\b", "narrativa de rodada"),
    ("processo", r"\bnesta sess(?:ão|ao)\b|\bin this session\b", "narrativa de sessao"),

    # -- autoelogio (§7) -----------------------------------------------------
    ("autoelogio", r"\bpadr(?:ão|ao) mais alto\b|\bhighest standard\b", "autoelogio"),
    ("autoelogio", r"\bmais rigoroso que\b|\bmore rigorous than\b", "autoelogio"),
]
LEXICO = [(c, re.compile(r, re.IGNORECASE), d) for (c, r, d) in LEXICO]

# -- depreciacao (§3): so vale como PAR, na mesma frase ---------------------
# Um repositorio do autor citado JUNTO de uma palavra de defeito. Separados,
# nenhum dos dois e achado: linkar o vizinho e legitimo, e falar de erro
# tambem. O defeito e a soma.
VIZINHO = re.compile(r"github\.com/mateusalkimim/([\w.-]+)", re.IGNORECASE)
DEFEITO = re.compile(
    r"\b(?:é falso|e falso|falsidade|errad[oa]|no ar até hoje|no ar ate hoje|"
    r"ninguém leu|ninguem leu|passou porque|it'?s false|is false|still up|"
    r"no one read|nobody read|wrong|mistaken)\b", re.IGNORECASE)

CATEGORIAS = ("papel", "componente", "rito", "infra", "processo",
              "autoelogio", "deprecia")

# --------------------------------------------------------------------------
# SEVERIDADE por (categoria, classe de superficie) -- norma §1
#
# "tela"   texto que a pessoa le: HTML publicado, README, docs/, valor
#          traduzido de traducao/*.json
# "codigo" comentario e docstring de .py/.js
# "dados"  o resto de um json versionado (metadado de build)
# "commit" mensagem de commit
#
# Em CODIGO, nome de componente/rito/infra e AVISO e nao bloqueio: ali a
# mencao costuma ter funcao tecnica (de onde veio o dado, que modelo gerou).
# Papel, processo, autoelogio e depreciacao bloqueiam em qualquer superficie.
# --------------------------------------------------------------------------
SEVERIDADE = {
    "tela":   {c: "bloqueio" for c in CATEGORIAS},
    "commit": {c: "bloqueio" for c in CATEGORIAS},
    "codigo": {"papel": "bloqueio", "processo": "bloqueio", "autoelogio": "bloqueio",
               "deprecia": "bloqueio", "componente": "aviso", "rito": "aviso",
               "infra": "aviso"},
    "dados":  {"papel": "bloqueio", "processo": "aviso", "autoelogio": "bloqueio",
               "deprecia": "bloqueio", "componente": "aviso", "rito": "aviso",
               "infra": "aviso"},
}

IGNORAR_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".github"}


def janela(txt, ini, fim, largura=110):
    """O entorno do TERMO, nao o comeco da linha.

    Numa pagina gerada uma linha pode carregar a folha inteira: imprimir os
    primeiros 150 caracteres mostra um texto que nada tem a ver com o achado,
    e o veredito sai errado por falta de contexto.
    """
    txt = " ".join(txt.split())
    # a posicao muda com a normalizacao: reacha o termo pelo conteudo
    termo = " ".join(txt[ini:fim].split()) if fim <= len(txt) else ""
    pos = txt.find(termo) if termo else -1
    if pos < 0:
        return txt[:largura * 2]
    a = max(0, pos - largura // 2)
    b = min(len(txt), pos + len(termo) + largura)
    return ("…" if a else "") + txt[a:b] + ("…" if b < len(txt) else "")


def sha(termo, trecho):
    return hashlib.sha1(
        (termo.strip().lower() + "|" + " ".join(trecho.split()).lower()
         ).encode("utf-8")).hexdigest()[:10]


def ler_excecoes(raiz):
    p = os.path.join(raiz, "publicacao-excecoes.txt")
    out = {}
    if not os.path.exists(p):
        return out
    for linha in io.open(p, encoding="utf-8"):
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        if "|" not in linha:          # excecao sem motivo nao vale
            continue
        k, motivo = linha.split("|", 1)
        if motivo.strip():
            out[k.strip()] = motivo.strip()
    return out


# --------------------------------------------------------------------------
# Extracao -- tudo devolve [(n_linha, texto)], com a linha PRESERVADA
# --------------------------------------------------------------------------
def _vazio_preservando_linhas(m):
    return "\n" * m.group(0).count("\n")


def comentarios_embutidos(bruto):
    """Comentario dentro de <style> e <script> da propria pagina.

    Buraco medido em 2026-08-28: a pagina publicada trazia, no CSS embutido,
    duas notas de producao com o papel interno dentro. O portao removia
    <style> e <script> inteiros para nao ler codigo, e junto ia o comentario
    — que e publicado, aparece em "ver codigo-fonte" e nao e menos publico por
    estar entre chaves.
    """
    out = []
    for m in re.finditer(r"(?is)<(script|style)\b[^>]*>(.*?)</\1>", bruto):
        linha0 = bruto[:m.start()].count("\n") + 1
        corpo = m.group(2)
        for c in re.finditer(r"/\*(.*?)\*/|//(.*?)$", corpo, re.S | re.M):
            txt = c.group(1) or c.group(2) or ""
            out.append((linha0 + corpo[:c.start()].count("\n"), " ".join(txt.split())))
    return out


def texto_de_html(bruto):
    s = re.sub(r"(?is)<script\b.*?</script>", _vazio_preservando_linhas, bruto)
    s = re.sub(r"(?is)<style\b.*?</style>", _vazio_preservando_linhas, s)
    # comentario de HTML tambem viaja para o navegador: fica, nao sai
    s = re.sub(r"(?s)<!--(.*?)-->", lambda m: " " + m.group(1) + " ", s)
    # alt/title/aria-label sao texto de tela
    s = re.sub(r"(?i)\b(?:alt|title|aria-label)\s*=\s*\"([^\"]*)\"",
               lambda m: " " + m.group(1) + " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return [(i + 1, _html.unescape(l)) for i, l in enumerate(s.split("\n"))]


def texto_de_md(bruto):
    return [(i + 1, l) for i, l in enumerate(bruto.split("\n"))]


def texto_de_py(caminho):
    """So comentario e docstring -- o codigo nao e prosa."""
    out = []
    try:
        with io.open(caminho, "rb") as fh:
            for tok in tokenize.tokenize(fh.readline):
                if tok.type == tokenize.COMMENT:
                    out.append((tok.start[0], tok.string))
                elif tok.type == tokenize.STRING and tok.line.strip().startswith(
                        ('"""', "'''", 'r"""', "u'''")):
                    for j, l in enumerate(tok.string.split("\n")):
                        out.append((tok.start[0] + j, l))
    except Exception:
        # arquivo que nao tokeniza: cai para as linhas de comentario simples
        for i, l in enumerate(io.open(caminho, encoding="utf-8",
                                      errors="replace").read().split("\n")):
            if l.lstrip().startswith("#"):
                out.append((i + 1, l))
    return out


def texto_de_js(bruto):
    out = []
    for i, l in enumerate(bruto.split("\n")):
        m = re.search(r"//(.*)$", l)
        if m:
            out.append((i + 1, m.group(1)))
        m = re.search(r"/\*(.*?)\*/", l)
        if m:
            out.append((i + 1, m.group(1)))
    return out


def texto_de_json(caminho, bruto):
    """Valor traduzido e TELA; o resto do json e metadado de build."""
    tela, dados = [], []
    linhas = bruto.split("\n")
    try:
        json.loads(bruto)
    except Exception:
        return tela, dados
    for i, l in enumerate(linhas):
        m = re.match(r'\s*"(pt|en|texto|label|titulo|title)"\s*:\s*"(.*)"[,]?\s*$', l)
        if m:
            tela.append((i + 1, m.group(2)))
        else:
            dados.append((i + 1, l))
    return tela, dados


def superficies(raiz):
    """[(caminho_relativo, classe, [(linha, texto)])] -- norma §1."""
    out = []
    for base, dirs, arqs in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in IGNORAR_DIRS and not d.startswith(".")]
        for a in sorted(arqs):
            p = os.path.join(base, a)
            rel = os.path.relpath(p, raiz)
            ext = os.path.splitext(a)[1].lower()
            if ext not in (".html", ".md", ".py", ".js", ".json", ".txt", ".css"):
                continue
            if a == "publicacao-excecoes.txt":
                continue
            try:
                bruto = io.open(p, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            if ext == ".html":
                out.append((rel, "tela", texto_de_html(bruto)))
                out.append((rel, "codigo", comentarios_embutidos(bruto)))
            elif ext in (".md", ".txt"):
                out.append((rel, "tela", texto_de_md(bruto)))
            elif ext == ".py":
                out.append((rel, "codigo", texto_de_py(p)))
            elif ext in (".js", ".css"):
                out.append((rel, "codigo", texto_de_js(bruto)))
            elif ext == ".json":
                tela, dados = texto_de_json(p, bruto)
                out.append((rel, "tela", tela))
                out.append((rel, "dados", dados))
    return out


def mensagens_de_commit(raiz, n):
    """Por padrao, o que este push levaria: @{u}..HEAD."""
    def git(*args):
        return subprocess.run(["git", "-C", raiz] + list(args),
                              capture_output=True, text=True)
    if n is None:
        r = git("log", "@{u}..HEAD", "--format=%H%n%B%n--fim--")
        if r.returncode != 0:
            return []
    else:
        r = git("log", "-%d" % n, "--format=%H%n%B%n--fim--")
        if r.returncode != 0:
            return []
    out, atual, sha_ = [], [], None
    for l in r.stdout.split("\n"):
        if l == "--fim--":
            if sha_:
                out.append((sha_[:8], "\n".join(atual)))
            atual, sha_ = [], None
        elif sha_ is None and re.fullmatch(r"[0-9a-f]{40}", l or ""):
            sha_ = l
        else:
            atual.append(l)
    return out


# --------------------------------------------------------------------------
def varrer_linhas(linhas, classe, origem, excecoes):
    achados, vistos = [], set()
    for n, txt in linhas:
        if not txt or not txt.strip():
            continue
        for cat, rx, o_que in LEXICO:
            for m in rx.finditer(txt):
                termo = m.group(0)
                ctx = janela(txt, m.start(), m.end())
                h = sha(termo, ctx)
                if h in excecoes or (origem, n, h) in vistos:
                    continue
                vistos.add((origem, n, h))
                achados.append({
                    "arquivo": origem, "linha": n, "categoria": cat,
                    "severidade": SEVERIDADE[classe][cat], "termo": termo,
                    "o_que": o_que, "sha": h, "trecho": ctx,
                })
        # §3 depreciacao: o par na MESMA frase
        for frase in re.split(r"(?<=[.!?])\s+", txt):
            viz = VIZINHO.search(frase)
            dfx = DEFEITO.search(frase)
            if viz and dfx:
                h = sha(viz.group(1), janela(frase, viz.start(), viz.end()))
                if h in excecoes:
                    continue
                achados.append({
                    "arquivo": origem, "linha": n, "categoria": "deprecia",
                    "severidade": SEVERIDADE[classe]["deprecia"],
                    "termo": "%s + '%s'" % (viz.group(1), dfx.group(0)),
                    "o_que": "afirma defeito de projeto irmao (§3)",
                    "sha": h, "trecho": janela(frase, viz.start(), viz.end()),
                })
    return achados


def conferir(raiz, commits=None):
    excecoes = ler_excecoes(raiz)
    achados = []
    for rel, classe, linhas in superficies(raiz):
        achados += varrer_linhas(linhas, classe, rel, excecoes)
    for sha_, msg in mensagens_de_commit(raiz, commits):
        achados += varrer_linhas([(1, l) for l in msg.split("\n")],
                                 "commit", "commit %s" % sha_, excecoes)
    return achados, excecoes


# --------------------------------------------------------------------------
# O CONTROLE -- negativo (tem de pegar) e positivo (nao pode acusar)
# --------------------------------------------------------------------------
ISCAS = [
    ("papel", "O operador decidiu que a figura fica."),
    ("papel", "Ratified by the operator in 2026-08-27."),
    ("papel", "e o padrao que esta casa ja aplicava em tres repositorios."),
    ("componente", "A norma vive na Hipatia, ao lado da Temis e do Delfos."),
    ("rito", "Os campos entram marcados como proposta e esperam ratificacao."),
    ("rito", "Quem achou foi o portao novo, o que clica em cada botao."),
    ("infra", "Os verbetes foram escritos pelo phi-4 rodando em /mnt/b/AITools."),
    ("processo", "Na primeira rodada: 48 propostos, 46 passaram, 34 aceitos."),
    ("autoelogio", "E o padrao mais alto que se consegue neste assunto."),
    ("deprecia", "No mapa irmao, o https://github.com/mateusalkimim/math-prerequisite-map, "
                 "um verbete afirma algo que e falso, e passou porque ninguem leu."),
]

# O controle POSITIVO. Sem ele o portao vira o que ele mesmo denuncia: uma
# sonda que acusa o certo. Toda frase daqui e uso LEGITIMO.
LIMPAS = [
    "It is the operator that creates geometry within algebra: from it come "
    "distance and angle, in any dimension.",
    "The operator maps a vector to another vector in the same space.",
    "Uma porta AND devolve 1 so quando as duas entradas valem 1.",
    "An AND gate outputs 1 only when both inputs are 1; NAND gates compose it.",
    "A proposta deste capitulo e mostrar o teorema antes da demonstracao.",
    "This is a proposal for how to read the diagram.",
    "O operador linear leva reta em reta e preserva a origem.",
    "Veja o repositorio companheiro em https://github.com/mateusalkimim/"
    "math-prerequisite-map para o mapa de pre-requisitos.",
    "Este texto esta errado e sera corrigido na proxima passada.",
    "A casa de Petzold no capitulo 12 usa reles em cascata.",
]


def controle():
    print("CONTROLE NEGATIVO -- cada isca TEM de ser pega:")
    falhou = []
    for esperado, frase in ISCAS:
        got = varrer_linhas([(1, frase)], "tela", "isca", {})
        cats = {a["categoria"] for a in got}
        ok = esperado in cats
        print("  %-3s [%s] %s" % ("ok" if ok else "NAO", esperado, frase[:64]))
        if not ok:
            falhou.append("isca nao pega (%s): %s" % (esperado, frase[:60]))

    print("\nCONTROLE POSITIVO -- nenhuma pode ser acusada:")
    for frase in LIMPAS:
        got = varrer_linhas([(1, frase)], "tela", "limpa", {})
        ok = not got
        print("  %-3s %s" % ("ok" if ok else "NAO", frase[:70]))
        if not ok:
            falhou.append("falso positivo em: %s -> %s" % (
                frase[:50], ", ".join("%s/%s" % (a["categoria"], a["termo"]) for a in got)))

    if falhou:
        print("\nCONTROLE REPROVADO (%d):" % len(falhou))
        for f in falhou:
            print("  · %s" % f)
        print("\nPortao quebrado. Zero achados nao vale nada enquanto isto nao passar.")
        return 1
    print("\nok: o portao pega o que tem de pegar e nao acusa o que e legitimo")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raiz", nargs="?", default=AQUI)
    ap.add_argument("--controle", action="store_true")
    ap.add_argument("--estrito", action="store_true", help="aviso tambem reprova")
    ap.add_argument("--commits", type=int, default=None,
                    help="confere as N ultimas mensagens (padrao: as nao empurradas)")
    a = ap.parse_args()
    if a.controle:
        return controle()

    raiz = os.path.abspath(a.raiz)
    achados, excecoes = conferir(raiz, a.commits)
    blo = [x for x in achados if x["severidade"] == "bloqueio"]
    avi = [x for x in achados if x["severidade"] == "aviso"]

    def mostrar(lista, titulo):
        if not lista:
            return
        print("\n%s (%d):" % (titulo, len(lista)))
        por_arquivo = {}
        for x in lista:
            por_arquivo.setdefault(x["arquivo"], []).append(x)
        for arq in sorted(por_arquivo):
            print("  %s" % arq)
            for x in sorted(por_arquivo[arq], key=lambda y: y["linha"]):
                print("    :%-5s %-10s %-8s %s" % (
                    x["linha"], x["categoria"], x["sha"], x["termo"]))
                print("           %s" % x["trecho"])

    print("registro publico — %s" % os.path.basename(raiz))
    print("  superficies lidas: %d · excecoes declaradas: %d"
          % (len(superficies(raiz)), len(excecoes)))
    mostrar(blo, "BLOQUEIO")
    mostrar(avi, "aviso")

    if blo or (a.estrito and avi):
        print("\nREPROVADO — %d bloqueio(s)%s. O push nao sai."
              % (len(blo), ", %d aviso(s) em modo estrito" % len(avi)
                 if a.estrito and avi else ""))
        print("Conserte o texto, ou declare a excecao em publicacao-excecoes.txt")
        print("com o sha ao lado do achado E o motivo. Excecao sem motivo nao vale.")
        return 1
    print("\nok: nenhuma superficie publica carrega registro interno%s"
          % (" (%d aviso)" % len(avi) if avi else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
