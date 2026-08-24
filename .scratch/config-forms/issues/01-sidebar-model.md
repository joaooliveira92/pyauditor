# Sidebar navigation model for multiple form families

- **Status:** resolved
- **Type:** wayfinder:grilling

## Question

Hoje a sidebar do Wayfinder (`src/ui/app.js`) só tem dois modos: uma lista
plana de arquivo raw, e uma árvore agrupada por indicador INMS (`<details>`
por `ind.key`, com um botão por órgão dentro). Com 3 famílias novas de
formulário chegando (categorias, datasets, contrato), como deve ficar o
agrupamento?

Decisão já tomada durante o charting (não re-abrir): agrupamento de topo por
família (INMS / Categorias / Datasets / Contrato), órgão como sub-nível só
onde a família tem um (INMS, categorias — datasets e contrato são arquivo
único). O que falta decidir aqui é a mecânica: layout exato dos grupos de
topo, como o filtro de busca (`#filter`) atravessa famílias, como o backend
expõe a lista das novas famílias (`/api/indicators` hoje só devolve INMS —
precisa de endpoint novo por família, ou um endpoint genérico?), e como
`state.mode` generaliza além de `"file"`/`"indicator"`.

Como este ticket carrega execução: a resolução inclui implementar a mudança
em `app.js`/`server.py`, não só desenhar.

## Answer

Layout: um `<div class="group-title">` + `<nav>` por família, na ordem
Indicators (INMS) / Categorias / Datasets / Contrato / Other files. INMS
mantém a árvore `<details>` existente. Categorias ganha dois botões fixos
(`MinC`/`MTur`) — sem endpoint de descoberta novo, o órgão é hardcoded no
frontend, mesmo padrão já usado pelo `<select>` de agência do painel de
pipeline (`index.html`, `<option>MinC</option>`/`<option>MTur</option>`).
Datasets e Contrato são singletons (um arquivo cada) — um botão de nav
cada, sem sub-lista, sem endpoint de descoberta.

Backend: nenhum endpoint genérico. Cada família ganhou seu próprio par
GET/PUT (`/api/categoria?orgao=`, `/api/datasets`, `/api/contrato`),
consistente com o padrão já estabelecido por `/api/indicator`.

`state.mode` generalizou para `file|indicator|categoria|dataset|contrato`.
`isDirty()`/`renderDirty()` generalizaram de `mode === "indicator"` para
`mode !== "file"` (todo modo não-`file` usa `state.formDirty`). O filtro de
busca (`#filter`) continua filtrando arquivos raw e a árvore INMS por texto;
Categorias/Datasets/Contrato não entram no filtro (2 e 2 singletons — YAGNI
pra busca textual num conjunto tão pequeno).

Efeito colateral: o form engine genérico do form INMS (`renderChildren`/
`renderNode`/`walkTarget`/`addItem`/`removeItem` em `app.js`) usava paths
como strings dot-joined (`"shared.config.target.value"`). Chaves de
categoria em `categorias.yaml` são literais como `"1.1"` (com ponto) — dot-
joining quebraria o parsing de path. Refeito pra path-as-array-de-chaves
(cada segmento guarda o tipo certo: string pra chave de objeto, number pra
índice de array), serializado via `JSON.stringify` num atributo `data-path`
e lido de volta com `JSON.parse` — elimina também a heurística antiga
`/^\d+$/` que podia confundir uma chave puramente numérica com índice de
array.

Implementado em `src/ui/server.py` (rotas) e `src/ui/app.js` (sidebar +
form engine generalizado). Ver ticket 03/04/05 para os endpoints e forms
específicos de cada família.
