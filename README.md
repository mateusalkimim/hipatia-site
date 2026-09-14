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

**→ [Abrir as apresentações](index.html)**

> **Estado: PROTÓTIPO.** O repositório é privado e não está no ar: o link acima
> abre o site **no clone** (notebook, tablet, qualquer pasta que tenha o
> repositório); no GitHub ele mostra só o arquivo. Em aberto: a versão em
> inglês do índice e dos decks (só o G3 a tem), o nome público e a
> hospedagem, se sair do clone local.

## Início rápido

Não há instalação. Baixe e abra:

```bash
git clone https://github.com/mateusalkimim/hipatia-site.git
cd hipatia-site
xdg-open index.html        # Linux · no macOS: open index.html · no Windows: duplo clique
```

Dentro de um seminário: **setas**, **espaço** ou *Page Down* avançam;
**F11** deixa a folha inteira. O botão **tema escuro** vale para o índice e
para a barra do visor; os decks são claros por norma de composição e não
mudam.

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

| grupo | seminários |
|---|---|
| 00 · a fundação | 0 O que é um número · 1 Duas operações · 2 Quem vem antes · 3 Negativos e a reta · 4 Divisibilidade e fatoração · 5 Números trigonométricos · 6 O círculo é um espelho · 7 A balança |
| 10 · arco GAAL | G1 Contar sem listar · G2 Determinantes · G3 Geometria analítica (pt-BR e inglês) · G4 Espaços vetoriais |
| 20 · arco do cálculo | C1 Ler um gráfico · C2 Antes da palavra limite · C3 Limites e continuidade · C4 O confronto |
| 90 · extras | Os dois pilares — um corte no tempo (documento, não aula) |

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
