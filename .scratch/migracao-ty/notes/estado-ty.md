# Estado do ty sobre o repo — factos do ticket 02

-   **Ticket:** 02-mapeamento-estado-ty · **Sessão:** research do esforço wayfinder `migracao-ty` (2026-08-22).
-   **Ferramenta:** `ty 0.0.73 (4bd2833c4 2026-08-18)`, montado por `uvx` (não instalado no `.venv`).
-   **Comando usado:** `uvx ty check --output-format concise src` e `... tests` (CLI do ty exige o subcomando `check`; `uvx ty check <caminhos>`).
-   **Config:** nada de `[tool.ty]` no `pyproject.toml` → ty usa defaults. O bloco `[tool.basedpyright]` existente é ignorado pelo ty.
-   **Baseline (controle):** `uv run basedpyright` → `0 errors, 0 warnings, 0 notes`. Tudo o que o ty reporta é delta sobre o estado "limpo" atual.

---

## Facto 1 — Mapa dos 32 suppresses → regras ty

Fato empírico que rege tudo: **`# type: ignore[<código mypy>]` não suprime nada no ty**. Pela doc de Suppression do ty, códigos sem o prefixo `ty:` são ignorados (só `# type: ignore` "puro", sem colchetes, suprime a linha inteira; e `type: ignore[ty:<rule>]` suprime a regra). Confirmado no próprio repo: `src/pyauditor/excel/capa.py:136` tem `# type: ignore[assignment]` e o ty reporta `invalid-assignment` na mesma linha. Logo o ty enxerga os 32 sites sem nenhuma supressão ativa (o default `respect-type-ignore-comments = true` não salva os códigos mypy).

### Tabela de mapeamento (código mypy → ty)

| Código mypy | Qtd sites | Regra ty equivalente | Comportamento sob o ty atual |
|---|---|---|---|
| `arg-type` | 15 | `invalid-argument-type` | Diagnóstico real; o ty reporta no site |
| `no-untyped-call` | 6 | **sem equivalente** (doc: cobre via Ruff `ANN`) | **0 diag** — comments mortos, removíveis |
| `misc` | 2 | `invalid-assignment` (caso concreto: propriedade read-only) | Diagnóstico real (2 sites: test_cli_main.py:42, test_periodo.py:51) |
| `dict-item` | 1 | `invalid-argument-type` (dict literal passado como arg) | Diagnóstico real |
| `assignment` | 2 | `invalid-assignment` | 1 site diagnostica (capa.py:136); 1 **morto** (split.py:338 — ty 0 diag) |
| `no-untyped-def` | 3 | **sem equivalente** (ty checa anotadas/não anotadas; Ruff `ANN`) | 0 diag — comments mortos, removíveis |
| `index` | 1 | `invalid-assignment` (atribuição em subscript de `Mapping`) | Diagnóstico real |
| `return-value` | 1 | `invalid-return-type` | Diagnóstico real |
| `call-arg` | 1 | `missing-argument`/`unknown-argument` (contribuiu) | 0 diag — comment morto (pydantic aceita **kwargs/extra) |

**Totais:** 21 dos 32 sites geram diagnóstico ty (e exigem `# ty: ignore[<rule>]` ou correção); **11 estão mortos sob o ty** (6 `no-untyped-call` + 3 `no-untyped-def` + 1 `assignment` em split.py:338 + 1 `call-arg` em test_models.py:52) e podem ser apenas removidos.

Detalhe por site (os que importam para o ticket 04):

-   `src/pyauditor/cli/consolidate.py:70` `[return-value]` → `invalid-return-type` (dict[str,str] vs dict[str,object]).
-   `src/pyauditor/engine/discovery.py:64` `[arg-type]` → `invalid-argument-type` (str vs `Literal["MinC","MTur"]`).
-   `src/pyauditor/excel/capa.py:136` `[assignment]` → `invalid-assignment` (`Cell.value` descriptor, union larga).
-   `src/pyauditor/cli/split.py:338` `[assignment]` → **morto** (0 diag — `config_path = None` já é legal para o ty).
-   `tests/test_inms_1_1_audit.py:437,462,478,481,493,700,701,744` `[arg-type]` → `invalid-argument-type` (cada chamada `write_sheet(..., **kwargs)` estoura 12-14 diag — um por overload do `write_sheet`). Uma única `# ty: ignore[invalid-argument-type]` por linha suprime todos.
-   `tests/test_logging.py:148,158,184` `[arg-type]` + `:160` `[dict-item]` → `invalid-argument-type` (testes deliberados de erro de runtime).
-   `tests/test_catalog.py:28` `[arg-type]` → `invalid-argument-type`; `:36` `[index]` → `invalid-assignment` (subscript em `Mapping`).
-   `tests/test_cli_split.py:414` `[arg-type]` → `invalid-argument-type` (**kwargs).
-   `tests/test_rom_summary.py:13` `[arg-type]` → `invalid-argument-type` (17 diag numa linha — **kwargs).
-   `tests/test_cli_main.py:42` `[misc]` → `invalid-assignment` (read-only pydantic);
-   `tests/test_periodo.py:51` `[misc]` → `invalid-assignment` (read-only pydantic).
-   `src/pyauditor/excel/inms_1_1/_cells.py:96,100` e `_sections_4_5.py:221,225,244,248` `[no-untyped-call]` → **morto** (0 diag; `CellIsRule` sem o ruído de outrora).
-   `tests/test_excel_consolidate.py:299,303,391` `[no-untyped-def]` → **morto** (0 diag).
-   `tests/test_models.py:52` `[call-arg]` → **morto** (0 diag).

---

## Facto 2 — Delta de diagnostics (ty com defaults sobre `src` + `tests`)

Total: **150 diagnostics**, todos `error`-level, exit 1. Nenhum deles aparece com a base line pyright strict clean (delta real medido).

### Por regra

| Regra ty | src | tests | total | natureza |
|---|---|---|---|---|
| `invalid-argument-type` | 1 | 132 | **133** | dívida real/teste-intencional; 1 delas em src |
| `invalid-assignment` | 1 | 4 | **5** | read-only pydantic (tests); capa.py (src) |
| `invalid-return-type` | 1 | – | **1** | dívida real em src |
| `unsupported-operator` | – | 8 | **8** | ruído de stub `types-openpyxl` (`cell.row`) |
| `no-matching-overload` | – | 3 | **3** | ruído de stub `types-openpyxl` (`sheet.cell`) |
| **Total** | **3** | **147** | **150** | |

### Por módulo

**src (3):**
- `cli/consolidate.py` 1 · `engine/discovery.py` 1 · `excel/capa.py` 1.

**tests (147):**
- `test_inms_1_1_audit.py` 115 (109 = `write_sheet(**kwargs)` nos sites de `arg-type` + 6 novos de stub: 177,331,809 `unsupported-operator`, 841/842/882 `no-matching-overload`)
- `test_rom_summary.py` 17 (1 site de **kwargs)
- `test_excel_sintetico.py` 5 (novos, stub `cell.row`)
- `test_logging.py` 4 · `test_catalog.py` 3 · `test_cli_main.py` 1 · `test_cli_split.py` 1 · `test_periodo.py` 1.

### Classificação real vs ruído

- **(a) Dívida de tipagem — 139 diag (src 3 + tests 136):** são os sites com `# type: ignore` existentes que agora afloram (tests de frozen pydantic, testes deliberados de erro em `logging`, chamadas com `**kwargs` em `write_sheet`/`IndicatorSummary`/`atomic_write`). O grosso vem fora do `**kwargs` em testes (12–17 diag por chamada, um por overload) — corrigir tipando o kwarg ou suprimindo a linha com `# ty: ignore[invalid-argument-type]`. Nada é "stub-error" neste lote.
- **(b) Ruído de stubs de terceiros — 11 diag (tests):** 8 `unsupported-operator` + 3 `no-matching-overload`, todos propagando `cell.row: int | None` do stub `types-openpyxl` (o stub declara `MergedCell.row → int | None` e `iter_rows` produz `_CellOrMergedCell`; `next(...cell.row...) + 1` fica `int | None + int`). São sites **sem `# type: ignore` existente** — novos, não existiam sob o basedpyright strict. Candidatos a `# ty: ignore[...]` justificado ou um `cast`/`int(...)` no site.
- **Caveat (delta honesto):** 11 dos 32 `# type: ignore` existentes viram mortos sob o ty (fato 1); o `unused-ignore-comment` não é ativado por default (0 warnings), mas entra como candidato do perfil strict para sinalizar os mortos.

---

## Facto 3 — Análise de equality/narrowing

- O default do ty (`strict-equality-semantics = false`) assume semântica "intuitiva" de `==`/`in`/`match`-value: narrow de `str` para `Literal["a"]` após `x == "a"`, e ignora subclassções/overrides de `__eq__`. O código usa isso o tempo todo: `entry.status == "running"` (status: `Literal[...]`), `command == "report"` (`command: str`), `calculation.aggregation == "sum"`, `config_dir.name == "_shared"`, `status_raw not in _VALID_STATES`. **Não há `match`-statements no repo** (todos os hits de "match" são `re.match`/`re.fullmatch`).
- **`strict-equality-semantics = true` → delta 0** (150 → 150, sem novos diagnostics). Não vale a pena ativá-la agora: o código já fecha com a semântica default, e ligar a flag só restringiria narrowing sem ganho imediato. Reavaliar se ticket 03 quiser "strict mais puro".
- **`strict-generic-narrowing = true` → +26 diag** (150 → 176): surgem `not-subscriptable` (14), `unresolved-attribute` (7) e mais `invalid-assignment`/`invalid-return-type`/`invalid-argument-type` propagados de `Top[list[...]]` (e.g. `src/pyauditor/interactive/provider.py` — `sorted(...)` com `object`; `tests/test_configs_shared_invariants.py`). **Recomendação: manter `false` na migração inicial** — só traz ruído.
- Verdicto: para ticket 03, o perfil estrito deve espelhar o default (regras quase todas ativas) + flags `[tool.ty.analysis]` AS DEFAULT (`strict-*` off), pois medido. Ini os números acima como rationale.

---

## Fato rápido — ambiente e instrumentação

- **Libs tipadas no `.venv`:** `pydantic`, `rich`, `loguru`, `questionary` têm `py.typed` (inline). `openpyxl` e `pyyaml` **não** têm mark; o ty resolve via `types-openpyxl` (`openpyxl-stubs/`) e `types-pyyaml` (`yaml-stubs/`), ambas instaladas. Todas as imports resolveram com ty usando o `.venv` do repo (nenhum `unresolved-import`).
- **Cache de ty:** nenhum diretório `.ty/`/`ty_cache` criado no repo durante os runs; ty não deixou cache no projeto (cachava fora do repo). O `.cache/` na raiz é do `zensical`/MkDocs (antigo, auto-gitignorado). **Nenhuma mudança necessária no `.gitignore`.**
- O ty default **exclui** `**/.mypy_cache/`, `**/.ruff_cache/`, `**/.venv/` etc. (lista default de `[tool.ty.src].exclude`) — diretórios de cache do repo já cobertos.
- Comandos para reproduzir: `uvx ty check --output-format concise src tests` (CLI: subcomando `check` é obrigatório).