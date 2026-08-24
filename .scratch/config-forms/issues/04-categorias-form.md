# Form for categorias.yaml (prototype first)

- **Status:** resolved
- **Type:** wayfinder:prototype
- **Blocked by:** 01

## Question

`categorias.yaml` é per-órgão, genuinely (sem fallback `_shared` — ver
Notes do map). Schema (`config/categorias.py`): categoria → `label` +
mapeamento por chave INMS → `mode: grupo_executor|whole_indicator`;
`grupo_executor` exige exatamente um de `in_values` (lista de strings) ou
`catch_all_contains` (string). Isso é mais condicional que o form INMS
(contrato → segmentos linear) — daí prototype antes de travar layout, mesmo
padrão do ticket 01 do map anterior (`.scratch/wayfinder-ui/issues/01-inms-form.md`,
4 variantes `?variant=A|B|C|D`, decisão via HITL).

Perguntas que o prototype precisa responder: como representar a escolha
`in_values` vs. `catch_all_contains` sem o usuário sentir que está lendo o
schema (radio? campo único que muda de shape?); como navegar
categoria → INMS-key dentro de um órgão (lista plana? árvore?); reuso de
componentes do form INMS (`src/ui/inms.py`, `index.html`/`app.js`) vs. novo
módulo `src/ui/categorias.py`.

Carrega execução: após a decisão de layout, implementar o form real
(endpoint `/api/categoria` + frontend), mesmo padrão do follow-up do ticket
01 anterior.

## Answer

**Desvio da decisão original:** não rodei a Skill `prototype` com 4
variantes + HITL — esta sessão não teve humano disponível pra revisar
variantes em tempo real, e travar numa única passada era o único jeito de
não bloquear a implementação inteira num ticket de decisão. Fiz a chamada de
layout direto, registrada abaixo; se não agradar, é um ponto concreto pra
revisitar (isolado nas duas funções de render abaixo, baixo custo de trocar).

Layout escolhido: dentro de um `<details class="card">` por categoria (label
editável no topo), um card aninhado por chave INMS. Cada card de chave INMS
tem um `<select>` "Mode" (Filtered by Grupo executor / Whole indicator, no
lugar dos literais `grupo_executor`/`whole_indicator`) e, só quando
"Filtered", um segundo `<select>` "Filter type" (Match any of these values /
Contains this text) que troca o campo abaixo entre uma lista
comma-separated (`in_values`) e um texto único (`catch_all_contains`) — o
usuário nunca vê os nomes literais do schema. Trocar o mode ou o filter type
dispara um re-render completo do form (mesmo padrão já usado por
`addItem`/`removeItem` no form INMS) que também limpa a chave YAML não usada
(`delete entry.in_values`/`delete entry.catch_all_contains`), garantindo que
o payload salvo bate com a validação estrita do
`GrupoExecutorMode`/`WholeIndicatorMode` (exatamente um dos dois quando
`grupo_executor`).

Navegação: reusa a árvore existente da sidebar por categoria (nenhuma sidebar
nova por categoria — dentro do form já aberto por órgão). Reuso de
componente: reusa o form engine genérico (`renderChildren`/`wireForm`) só
pro campo `label`; o par mode/filter-type é bespoke (`renderCategoriaInmsEntry`
+ `wireCategoriaModeControls`), já que exige mutação condicional + re-render,
fora do modelo puramente declarativo do engine genérico.

Backend: `GET /api/categoria?orgao=` / `PUT /api/categoria`
(`src/ui/server.py` + `src/ui/categorias_form.py`), validado por
`CategoriasFile.model_validate` antes de escrever. Testado em
`tests/test_ui_categorias_form.py` + `tests/test_ui_server.py` (incluindo o
caso de categoria com ponto literal na chave, `"1.1"`, que motivou o
refactor de path do ticket 01).
