# Apresentações — `hipatia-site`

**Um site estático que reúne os dezessete seminários da série "Um curso de
visão computacional e geometria da imagem", em árvore.** Abre com dois cliques
no navegador, funciona **offline**, sem servidor, sem conta e sem biblioteca
de rede: os decks são HTML com figuras ao lado, e a única dependência é uma
cópia local do MathJax, que já vem no repositório.

A árvore é o argumento: a **fundação** (oito seminários) alimenta dois arcos
que não dependem um do outro — **GAAL**, sobre o que uma transformação
*preserva*, e **Cálculo**, sobre o que acontece *perto de um ponto*. O índice
desenha essa ordem; o visor abre um deck de cada vez com os vizinhos ao lado.

<!-- site:inicio — gerado por gerar_site.py; não edite à mão -->
**→ [Abrir as apresentações](https://mateusalkimim.github.io/hipatia-site/)**

> **Estado: PROTÓTIPO.** No ar pelo GitHub Pages; também abre do clone,
> sem servidor. Em aberto: a versão em inglês do índice e dos decks
> (só o G3 a tem).
<!-- site:fim -->

## Início rápido

Não há instalação. Baixe e abra:

```bash
git clone https://github.com/mateusalkimim/hipatia-site.git
cd hipatia-site
xdg-open index.html        # Linux · no macOS: open index.html · no Windows: duplo clique
```

O índice desenha a árvore, numera os três passos e traz um botão de começo
que passa a **lembrar onde a leitura parou**. Cada cartão abre o seminário
no visor; no pé ficam o PDF, a versão em inglês quando existe e "só o deck",
que abre a apresentação sozinha.

No visor: **setas**, **espaço** ou *Page Down* avançam; na última folha, a
seta de novo abre o seminário seguinte. A barra mostra a posição na série,
a folha atual com uma linha de progresso, os vizinhos **pelo nome**, e o
sumário inteiro fica ao lado em tela larga (gaveta em tela estreita). <kbd>?</kbd>
lista os atalhos; ⛶ põe em tela cheia. O interruptor **Tema escuro** fica à
vista em todas as páginas e vale para a moldura; os decks são claros por
norma de composição e não mudam. Os decks copiados recebem uma **ponte** de
poucas linhas que conversa com o visor (folha atual, salto, gesto de
arrastar); fora do visor ela não faz nada.

## O que tem aqui

```
index.html              o índice, em árvore                       (gerado)
ver.html                o visor: barra + o deck num quadro        (gerado)
decks/<pasta>/          um HTML por seminário e SÓ as figuras que ele usa (gerado)
pdf/                    os PDFs 16:9, com o nome de apresentação  (gerado)
vendor/tex-svg.js       MathJax, uma cópia para todos             (gerado)
gerar_site.py           o gerador — a única coisa que se edita aqui
conferir_publicacao.py  conferência de vocabulário para superfície pública
docs/INSTALACAO.md      como regenerar a partir do material de origem
```

Cada seminário, com os três jeitos de abrir: no **visor** (barra, sumário,
retomada), o **deck** sozinho, e o **PDF**:

<!-- catalogo:inicio — gerado por gerar_site.py; não edite à mão -->
| # | seminário | abrir | PDF |
|---|---|---|---|
| | **00 · a fundação** | | |
| 0 | O que é um número — a ideia, a escrita e o sinal | [visor](https://mateusalkimim.github.io/hipatia-site/ver.html?d=0) · [deck](https://mateusalkimim.github.io/hipatia-site/decks/seminario-0b-o-que-e-um-numero/seminario-0b.html) | [PDF](https://mateusalkimim.github.io/hipatia-site/pdf/0%20%C2%B7%20O%20que%20%C3%A9%20um%20n%C3%BAmero.pdf) |
| 1 | Duas operações — a aritmética que sustenta os dois arcos | [visor](https://mateusalkimim.github.io/hipatia-site/ver.html?d=1) · [deck](https://mateusalkimim.github.io/hipatia-site/decks/seminario-0-duas-operacoes/seminario-0-duas-operacoes.html) | [PDF](https://mateusalkimim.github.io/hipatia-site/pdf/1%20%C2%B7%20Duas%20opera%C3%A7%C3%B5es.pdf) |
| 2 | Quem vem antes — a ordem que a soma define | [visor](https://mateusalkimim.github.io/hipatia-site/ver.html?d=2) · [deck](https://mateusalkimim.github.io/hipatia-site/decks/seminario-0f-quem-vem-antes/seminario-0f.html) | [PDF](https://mateusalkimim.github.io/hipatia-site/pdf/2%20%C2%B7%20Quem%20vem%20antes%20%E2%80%94%20a%20ordem%20que%20a%20soma%20define.pdf) |
| 3 | Negativos e a reta — a ordem e a distância | [visor](https://mateusalkimim.github.io/hipatia-site/ver.html?d=3) · [deck](https://mateusalkimim.github.io/hipatia-site/decks/seminario-0e-negativos-e-a-reta/seminario-0e.html) | [PDF](https://mateusalkimim.github.io/hipatia-site/pdf/3%20%C2%B7%20Negativos%20e%20a%20reta%20%E2%80%94%20a%20ordem%20e%20a%20dist%C3%A2ncia.pdf) |
| 4 | Divisibilidade e fatoração — quem divide quem | [visor](https://mateusalkimim.github.io/hipatia-site/ver.html?d=4) · [deck](https://mateusalkimim.github.io/hipatia-site/decks/seminario-0d-divisibilidade-e-fatoracao/seminario-0d.html) | [PDF](https://mateusalkimim.github.io/hipatia-site/pdf/4%20%C2%B7%20Divisibilidade%20e%20fatora%C3%A7%C3%A3o%20%E2%80%94%20quem%20divide%20quem.pdf) |
| 5 | Números trigonométricos — três razões que não mudam de tamanho | [visor](https://mateusalkimim.github.io/hipatia-site/ver.html?d=5) · [deck](https://mateusalkimim.github.io/hipatia-site/decks/seminario-0c-numeros-trigonometricos/seminario-0c.html) | [PDF](https://mateusalkimim.github.io/hipatia-site/pdf/5%20%C2%B7%20N%C3%BAmeros%20trigonom%C3%A9tricos.pdf) |
| 6 | O círculo é um espelho — três números, e o resto é reflexão | [visor](https://mateusalkimim.github.io/hipatia-site/ver.html?d=6) · [deck](https://mateusalkimim.github.io/hipatia-site/decks/seminario-0g-o-circulo-e-um-espelho/seminario-0g.html) | [PDF](https://mateusalkimim.github.io/hipatia-site/pdf/6%20%C2%B7%20O%20c%C3%ADrculo%20%C3%A9%20um%20espelho%20%E2%80%94%20tr%C3%AAs%20n%C3%BAmeros%2C%20e%20o%20resto%20%C3%A9%20reflex%C3%A3o.pdf) |
| 7 | A balança — fazer o mesmo nos dois lados | [visor](https://mateusalkimim.github.io/hipatia-site/ver.html?d=7) · [deck](https://mateusalkimim.github.io/hipatia-site/decks/seminario-0h-a-balanca/seminario-0h.html) | [PDF](https://mateusalkimim.github.io/hipatia-site/pdf/7%20%C2%B7%20A%20balan%C3%A7a%20%E2%80%94%20fazer%20o%20mesmo%20nos%20dois%20lados.pdf) |
| | **10 · arco GAAL — o que se PRESERVA** | | |
| G1 | Contar sem listar — a combinatória que o determinante cobra | [visor](https://mateusalkimim.github.io/hipatia-site/ver.html?d=G1) · [deck](https://mateusalkimim.github.io/hipatia-site/decks/seminario-g1-contar-sem-listar/seminario-g1-contar-sem-listar.html) | [PDF](https://mateusalkimim.github.io/hipatia-site/pdf/G1%20%C2%B7%20Contar%20sem%20listar.pdf) |
| G2 | Determinantes — o número que mede o avesso | [visor](https://mateusalkimim.github.io/hipatia-site/ver.html?d=G2) · [deck](https://mateusalkimim.github.io/hipatia-site/decks/seminario-determinantes/seminario-determinantes.html) | [PDF](https://mateusalkimim.github.io/hipatia-site/pdf/G2%20%C2%B7%20Determinantes%20%E2%80%94%20o%20n%C3%BAmero%20que%20mede%20o%20avesso.pdf) |
| G3 | Geometria analítica — do registro ao pixel | [visor](https://mateusalkimim.github.io/hipatia-site/ver.html?d=G3) · [deck](https://mateusalkimim.github.io/hipatia-site/decks/seminario-geometria/seminario.html) · [English version](https://mateusalkimim.github.io/hipatia-site/ver.html?d=G3&v=en) | [PDF](https://mateusalkimim.github.io/hipatia-site/pdf/G3%20%C2%B7%20Geometria%20anal%C3%ADtica%20%E2%80%94%20do%20registro%20ao%20pixel.pdf) |
| G4 | Espaços vetoriais — a sacola e o que não vaza | [visor](https://mateusalkimim.github.io/hipatia-site/ver.html?d=G4) · [deck](https://mateusalkimim.github.io/hipatia-site/decks/seminario-espacos-vetoriais/seminario-espacos-vetoriais.html) | [PDF](https://mateusalkimim.github.io/hipatia-site/pdf/G4%20%C2%B7%20Espa%C3%A7os%20vetoriais%20%E2%80%94%20a%20sacola%20e%20o%20que%20n%C3%A3o%20vaza.pdf) |
| | **20 · arco do cálculo — PERTO DE UM PONTO** | | |
| C1 | Ler um gráfico — a leitura que o cálculo cobra e ninguém ensina | [visor](https://mateusalkimim.github.io/hipatia-site/ver.html?d=C1) · [deck](https://mateusalkimim.github.io/hipatia-site/decks/seminario-calculo-0-ler-um-grafico/seminario-calculo-0.html) | [PDF](https://mateusalkimim.github.io/hipatia-site/pdf/C1%20%C2%B7%20Ler%20um%20gr%C3%A1fico.pdf) |
| C2 | Antes da palavra limite — Arquimedes, Fermat e o cálculo sem o conceito | [visor](https://mateusalkimim.github.io/hipatia-site/ver.html?d=C2) · [deck](https://mateusalkimim.github.io/hipatia-site/decks/seminario-calculo-1-antes-do-limite/seminario-calculo-1.html) | [PDF](https://mateusalkimim.github.io/hipatia-site/pdf/C2%20%C2%B7%20Antes%20da%20palavra%20limite.pdf) |
| C3 | Limites e continuidade — limites e continuidade | [visor](https://mateusalkimim.github.io/hipatia-site/ver.html?d=C3) · [deck](https://mateusalkimim.github.io/hipatia-site/decks/seminario-calculo-2-limites-e-continuidade/seminario-calculo-2.html) | [PDF](https://mateusalkimim.github.io/hipatia-site/pdf/C3%20%C2%B7%20Limites%20e%20continuidade.pdf) |
| C4 | O confronto — propriedades e o Teorema do Confronto | [visor](https://mateusalkimim.github.io/hipatia-site/ver.html?d=C4) · [deck](https://mateusalkimim.github.io/hipatia-site/decks/seminario-calculo-3-o-confronto/seminario-calculo-3.html) | [PDF](https://mateusalkimim.github.io/hipatia-site/pdf/C4%20%C2%B7%20O%20confronto.pdf) |
| | **90 · extras** | | |
| map | Os dois pilares — um corte no tempo | [visor](https://mateusalkimim.github.io/hipatia-site/ver.html?d=map) · [deck](https://mateusalkimim.github.io/hipatia-site/decks/mapa-genealogia/mapa-genealogia.html) | [PDF](https://mateusalkimim.github.io/hipatia-site/pdf/Os%20dois%20pilares%20%E2%80%94%20um%20corte%20no%20tempo.pdf) |
<!-- catalogo:fim -->

## De onde vem, e como se regenera

Os decks **não nascem aqui**. A fonte é a pasta de material da série, no
computador do autor; este repositório é a **saída** de `gerar_site.py`, que
lê o catálogo de lá (uma lista só, no lugar onde ela já vivia), copia cada
HTML com as figuras que ele referencia e reescreve as referências que saem
da pasta do deck. Ver `docs/INSTALACAO.md`.

Regra de ouro: **editar o gerado é o defeito**. A próxima rodada apaga
`decks/`, `pdf/`, `vendor/` e reescreve as duas páginas. Mexa no deck de
origem ou no gerador.

## Garantias, e o que elas não cobrem

- **nenhuma figura quebrada**: o gerador confere toda referência de todo
  HTML gerado e **falha alto** se uma não existir na saída;
- **nada sai da máquina ao abrir**: nenhum `<link>`, `@import`, fonte ou
  script de rede — o tipo é o do sistema (Georgia e Inter quando houver);
- **o PDF é a mesma sequência do HTML** quando foi gerado depois dele; se
  estiver mais velho, o gerador avisa no terminal e o PDF entra assim mesmo;
- o que **não** se afirma: nenhum efeito de aprendizagem foi medido com
  estudantes. O site organiza o material; não prova que ele ensina.

## Licença

Código sob **MIT** (`LICENSE`). Conteúdo dos seminários sob
**CC BY-SA 4.0** (`LICENSE-CONTENT`), **exceto** as figuras de terceiros
creditadas dentro de cada deck (cartazes e stills de filmes no G3, páginas
de caderno de desenho), que seguem com seus donos.
