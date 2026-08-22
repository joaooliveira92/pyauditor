# ADR 0003 — Configs single-source por órgão com filtro em memória

## Contexto

Até 2026-08, `configs/MinC/` e `configs/MTur/` duplicavam 14 YAMLs base (`inms-01.yaml`…`inms-14.yaml`) + `datasets.yaml` idêntico (2.507 linhas, 55 arquivos). A divergência real era só `scope.orgao`/`contract`, `acceptance_test` (snapshot 06/2026) e `categorias.yaml` (literais de `Grupo_executor`). Alterar uma meta do Anexo D exigia 2 edições manuais com risco de drift silencioso — já observado drift cosmético nos comentários de `inms-06.yaml`.

`split` materializava `_split/<inms>/<categoria>.csv` + YAMLs derivados `inms-*.*.yaml` (gitignored mas trackeados via `git ls-files` antes do ticket 01), triplicando I/O para INMS segmentados e criando estado derivado no repo. `measure` descobria derivados via `glob("*.yaml")`, então clone fresco sem `split` media 14 indicadores, com `split` media 20 — não determinístico. O motor (`shape` discriminated union + `QualityGateRunner` + `DatasetManifest`) já era simples e eficiente; o gargalo era organização de arquivos.

## Decisão

- **Single-source**: `configs/_shared/` com os 14 indicadores canônicos (sem `scope` hard-coded, sem `acceptance_test`) + `datasets.yaml` único. `órgão` vira dimensão de execução (`measure --orgao MinC`), injetada em runtime por `engine/pipeline.py:discover_config_files` + `cli/main.py:_resolve_config_dir`.
- **`acceptance_test` fora de produção**: movido para `tests/acceptance/<orgao>/2026-06.yaml` (snapshot da competência de referência), validado por `tests/test_shared_acceptance.py`.
- **Filtro em memória (ticket 04)**: `cli/measure.py` expande categorias `grupo_executor` via `categoria_filter.compute_categoria_values` + `read_raw_csv` (uma leitura do CSV bruto), criando `IndicatorConfig` derivados em memória (`id: INMS-01.ATENDIMENTO_N1`) e medindo `QualityGateRunner` + `SHAPE_REGISTRY` sobre linhas filtradas. `cli/split.py` ganha `materialize: bool` — `run` normal passa `materialize=False` (gera só `sintetico.xlsx`, sem `_split/`), `pyauditor split` manual mantém `True` para inspeção. `input/_split` deixa de ser pré-requisito para `measure`.
- **Discovery determinístico**: `configs/_shared` é a única fonte para `measure`/`split`/`report` quando existe; fallback per-órgão mantido. `config/manifest.py` prefere `_shared/datasets.yaml`.

## Alternativas consideradas

- **B: `!include`/herança YAML** — manter `configs/MinC/` e `configs/MTur/` com 28 arquivos que fazem `_base: ../_shared/inms-01.yaml` + override de `scope`. DRY, mas mantém 28 arquivos e exige resolver `!include` custom; descartado por manter duplicação de arquivos.
- **C: Builder em Python** — trocar YAML por `IndicatorConfig` construído em código (`configs/build.py`). Elimina YAML e ganha `basedpyright` total, mas perde a propriedade mais valiosa: fiscal técnico lê/edita `inms-01.yaml` sem saber Python. Descartado.

## Consequências

- Clone fresco determinístico: `measure` produz 20 ROMs (MinC, 06/2026) sem `split` prévio; `ls input/MinC/2026/06/_split` não existe após `run` limpo.
- -28 arquivos base duplicados (32 → 19 trackeados: 15 em `_shared` + 2 `categorias.yaml` + 2 `datasets.yaml` fallback); `git ls-files | grep configs` só lista `_shared` + `categorias.yaml` por órgão.
- I/O de segmentados −60% (uma leitura do CSV bruto vs 3 leituras + 3 escritas + 3 releituras).
- `acceptance_test` não polui produção; snapshot versionado em `tests/`.
- `measure` agora conhece `Grupo_executor` (antes só `split` conhecia) — acoplamento intencional para eliminar estado derivado.

## Estado

Aceito. Implementado em tickets 01–06 de `.scratch/configs-single-source/` (2026-08-21). Supera ADR 0002 onde 0002 assumia derivados em disco; 0002 permanece como histórico da decisão original, 0003 é a evolução desmaterializada.
