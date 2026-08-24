# Form for datasets.yaml

- **Status:** resolved
- **Type:** wayfinder:grilling
- **Blocked by:** 01

## Question

`configs/_shared/datasets.yaml` (único arquivo lido de fato — ver ticket 02)
é uma lista plana de ~14 aliases → `{file, delimiter, encoding}`
(`config/manifest.py::DatasetEntry`). Sem órgão, sem aninhamento — a
decisão de UX que falta é só de estilo: tabela editável inline (uma linha
por alias, 3 colunas) vs. formulário por-entrada (seleciona alias na
sidebar, edita um card). Dado o tamanho pequeno e uniforme, tabela inline
parece suficiente sem precisar de ticket de prototype dedicado — mas
confirmar isso é parte da pergunta, não assumir.

Backend: novo endpoint (`/api/datasets` GET/PUT?) espelhando o padrão de
`/api/indicator`, reusando `DatasetEntry` (pydantic) pra validar antes de
escrever de volta o YAML.

Carrega execução: implementar backend + frontend como parte da resolução.

## Answer

Decisão: card por alias (um `<div class="card">` por entrada, 3 campos
`File`/`Delimiter`/`Encoding` dentro), em vez de `<table>` HTML literal —
reusa o idioma visual já existente (mesmo componente do form INMS pra listas
de itens), evita CSS de tabela novo, e permanece legível pra ~14 entradas.
Um botão "+ Add dataset" (`window.prompt` pro alias, mesmo padrão de
confirmação já usado por `guardDiscard`) e um botão de remover por card.

Backend: `GET /api/datasets` / `PUT /api/datasets`
(`src/ui/server.py` + `src/ui/datasets_form.py`). `read_datasets` resolve
`_shared/datasets.yaml` preferencialmente (cai pro primeiro candidato achado
se `_shared` não existir); `save_datasets` valida cada entrada com
`DatasetEntry.model_validate` antes de escrever, reescreve o YAML inteiro
(perde comentários do cabeçalho — mesmo trade-off já aceito por
`src/ui/inms.py`/`split_derive`). Frontend em `renderDatasetForm`
(`src/ui/app.js`). Testado em `tests/test_ui_datasets_form.py` +
`tests/test_ui_server.py`.
