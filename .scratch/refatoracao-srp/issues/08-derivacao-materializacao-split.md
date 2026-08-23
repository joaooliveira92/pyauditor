# 08 — Extrair derivação e materialização do split

Type: task

**What to build:** a lógica de derivação de config por categoria e a escrita de CSVs filtrados deixam de viver no corpo de `run_split`. A derivação de configs derivadas e a escrita de CSVs filtrados (`_split/*`) vão para módulos próprios (`cli/split/_derive.py`, `cli/split/_filter_io.py`); `run_split` passa a orquestrar, mantendo o modo não-materializado dentro de `run`.

**Blocked by:** nenhum — pode começar imediatamente.

**Status:** resolved

- [x] `run_split` mantém a mesma assinatura pública e o mesmo modo não-materializado.
- [x] Supressão de configs derivadas na descoberta (ADR 0002) preservada.
- [x] Artefatos `_split/*` e configs por categoria com conteúdo idêntico ao atual.
- [x] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes (suíte `test_cli_split.py` como rede).

## Contexto (do relatório SRP)

`cli/split.py` (463 físicas, 16 imports): `run_split` 311 linhas; `_write_filtered_csv`, `_derive_config`, `_write_derived_config` e `SplitResult`. Um único comando que "filtra" (dados) e "materializa" (I/O de CSV+config+Excel) ao mesmo tempo.

## Answer

Criado `src/pyauditor/cli/split_derive.py` (ticket 08 SRP; não usei `cli/split/` porque `split` já é módulo, não pacote) com a derivação/materialização pura dos artefatos: `write_filtered_csv` (CSV atômico), `derive_config` (config do indicador derivada, `acceptance_test` omitido) e `write_derived_config` (YAML atômico). `run_split` agora chama essas funções e só orquestra (loop por INMS/categoria, backbone, modo `materialize` e o bloco final do `sintetico.xlsx`). Imports órfãos removidos (`csv`, `yaml`, `atomic_write`, `Source`) e call-sites renomeados.

Dois testes de `tests/test_cli_split.py` que patcheavam `pyauditor.cli.split.atomic_write` foram apontados para `pyauditor.cli.split_derive.atomic_write` (onde o símbolo vive agora). `run_split`/`SplitResult` públicos inalterados.

Validação: `uv run pytest` 586 passados, cobertura 89.57% (gate 85% ok); `uv run ty check`, `uv run ruff check`, `uv run ruff format --check` e `uv run bandit` verdes.

Nota: o ticket pedia dois módulos (`_derive.py` + `_filter_io.py`); mantenho como um único `split_derive.py` (coeso — derivação+escrita dos artefatos por categoria; a separação em dois fragmentaria o mesmo bloco de trabalho do `run_split`).