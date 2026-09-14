# Instalação

Não há instalação para **usar**. Baixe o repositório e abra o `index.html`.
Funciona offline, sem servidor e sem dependência.

## Usar

### Windows

1. baixe o repositório — **Code → Download ZIP** no GitHub, ou
   `git clone https://github.com/mateusalkimim/hipatia-site.git`;
2. extraia, se baixou o ZIP;
3. **duplo clique** em `index.html`.

### Linux

```bash
git clone https://github.com/mateusalkimim/hipatia-site.git
cd hipatia-site
xdg-open index.html
```

### macOS

```bash
git clone https://github.com/mateusalkimim/hipatia-site.git
cd hipatia-site
open index.html
```

### Com servidor local (opcional)

Alguns navegadores em celular não abrem um quadro (`iframe`) a partir de
`file://`. Aí um servidor mínimo resolve:

```bash
python3 -m http.server 8000      # depois abra http://localhost:8000/
```

## Regenerar

Só quem tem o material de origem regenera. O gerador lê o catálogo de
`ferramentas/preparar_entrega.py` e de `material/episodios.py`, que moram
ao lado da pasta de material:

```bash
python3 gerar_site.py                                    # caminho padrão
python3 gerar_site.py --material /caminho/hipatia/material
python3 gerar_site.py --sem-pdf                          # sem copiar os PDFs
```

Ele apaga `decks/`, `pdf/` e `vendor/`, copia de novo, reescreve `index.html`
e `ver.html`, e **termina com erro** se alguma referência de um deck não
existir na saída. Precisa só de Python 3 — nenhuma biblioteca.

Antes de publicar qualquer coisa fora do clone:

```bash
python3 conferir_publicacao.py --controle    # primeiro o controle
python3 conferir_publicacao.py --commits 3   # depois o repositório e as mensagens
```
