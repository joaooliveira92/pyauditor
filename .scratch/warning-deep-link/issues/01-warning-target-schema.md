# Warning target schema + code-to-target builders

- **Status:** resolved
- **Type:** wayfinder:task

## Question

`Warning` (`src/pyauditor/categoria_filter.py`) and its wire form
`WarningJson` (`orchestration/summary_json.py`) carry `code`/`orgao`/
`competencia`/`inms_key`/`categoria` but nothing that says which UI field a
warning points at. Decisão do charting (não re-abrir): o mapeamento
código→alvo vive do lado do servidor, não numa tabela hardcoded no
`app.js` — a UI só deve consumir um `target` já resolvido.

Adicionar um campo `target: WarningTargetJson | None` a `WarningJson`
(`family`, `orgao`, `path` — `path` na mesma convenção de array-de-chaves já
usada pelo form engine genérico do `app.js` desde o `config-forms`, ex.:
`["config", "categorias", "ATENDIMENTO_N1", "inms", "1.1", "in_values"]`).
Implementar os dois builders que hoje têm alvo resolvível:

- `in_values_unmatched` (`unmatched_in_values_warnings`) → aponta pro campo
  `in_values` daquele `categoria_key`/`inms_key` específico.
- `outros_leftover` (`outros_warning`) → **não tem alvo** (`categoria`
  "outros" não é uma entrada editável de `categorias.yaml` — já é termo
  canônico do `CONTEXT.md`); `target` fica `None`.

Qualquer warning ainda `code="unstructured"` também fica com `target=None`
— não é este ticket que migra mais códigos (ver "Out of scope" do map).

Carrega execução: implementar `Warning`/`WarningJson` + os dois builders +
testes (`tests/test_categoria_filter.py` ou onde os testes atuais de
`unmatched_in_values_warnings`/`outros_warning` já vivem).

## Answer

Implementado. Novo dataclass `WarningTarget` (`family`, `orgao`, `path:
tuple[str, ...]`) em `categoria_filter.py`; `Warning` ganhou o campo
`target: WarningTarget | None = None`.

- `unmatched_in_values_warnings` monta o `target`: `family='categorias'`,
  `orgao=orgao`, `path=('config', 'categorias', categoria_key, 'inms',
  inms_key, 'in_values')` — mesma convenção de array-de-chaves do form
  engine genérico (`app.js`, confirmada lendo o código: o form de
  categorias já usa exatamente esse `base` pra `data-path`).
- `outros_warning` não seta `target` (fica `None` pelo default) — "outros"
  não é entrada editável, como já decidido no charting.

Espelhado no wire form: `WarningTargetJson` (`family`, `orgao`, `path:
list[str]`) adicionado em `summary_json.py`; `WarningJson` ganhou
`target: WarningTargetJson | None`; `_all_warnings` serializa
`warning.target` pro dict ou `None`.

Testes: `tests/test_categoria_filter.py` cobre o `target` resolvido em
`unmatched_in_values_warnings` e `target is None` em `outros_warning`.
`tests/test_orchestration_summary.py` ganhou
`test_all_warnings_serializes_target`, testando a serialização de
`_all_warnings` direto (com um `RunResult`/result fakes) pros dois casos
(com e sem `target`). Suite completa (`uv run pytest`) e `ruff check`
passam; os erros de `mypy` em `summary_json.py` são pré-existentes (mesmos
antes desta mudança, confirmado com `git stash`).
