# 07 — Extrair loop de medição e ROMs combinados do measure

Type: task

**What to build:** o processamento por indicador deixa de ser closure com estado mutável. `_handle_result` e `_hard_fail_todas_categorias` viram funções puras que retornam estado (`outcomes`, `warnings`), sem `nonlocal`; o loop de medição vai para um módulo próprio (`cli/measure/_runner.py`); `write_combined_roms` para outro módulo (`cli/measure/_combined.py`). `run_measure` orquestra chamando os módulos.

**Blocked by:** 06 — resolução de entradas do measure.

**Status:** ready-for-agent

- [ ] Nenhum `nonlocal` no caminho de medição.
- [ ] Comportamento de hard-failure (todas as categorias) e de warnings idêntico ao atual.
- [ ] `write_combined_roms` com mesma assinatura para os consumidores de `summary*`.
- [ ] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes.

## Contexto (do relatório SRP)

Parte 2 da divisão do hub CRÍTICO `cli/measure.py`. O maior risco são as closures `nonlocal`; exige primeiro transformá-las em funções puras com retorno de estado, depois mover. Suíte `test_cli_measure.py` (1006 linhas) como rede de aceitação end-to-end.