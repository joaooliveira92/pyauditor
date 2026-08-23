# 08 — Extrair derivação e materialização do split

Type: task

**What to build:** a lógica de derivação de config por categoria e a escrita de CSVs filtrados deixam de viver no corpo de `run_split`. A derivação de configs derivadas e a escrita de CSVs filtrados (`_split/*`) vão para módulos próprios (`cli/split/_derive.py`, `cli/split/_filter_io.py`); `run_split` passa a orquestrar, mantendo o modo não-materializado dentro de `run`.

**Blocked by:** nenhum — pode começar imediatamente.

**Status:** ready-for-agent

- [ ] `run_split` mantém a mesma assinatura pública e o mesmo modo não-materializado.
- [ ] Supressão de configs derivadas na descoberta (ADR 0002) preservada.
- [ ] Artefatos `_split/*` e configs por categoria com conteúdo idêntico ao atual.
- [ ] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes (suíte `test_cli_split.py` como rede).

## Contexto (do relatório SRP)

`cli/split.py` (463 físicas, 16 imports): `run_split` 311 linhas; `_write_filtered_csv`, `_derive_config`, `_write_derived_config` e `SplitResult`. Um único comando que "filtra" (dados) e "materializa" (I/O de CSV+config+Excel) ao mesmo tempo.