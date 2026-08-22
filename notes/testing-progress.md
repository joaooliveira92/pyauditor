# Testing progress

## Latest run

- Date: 2026-08-22
- Objective: Fechar o wayfinder `migracao-ty` por completo — ticket 03 (perfil `ty`), ticket 04 fatia `ruff check`, e ticket 04 fatia `ty check`
- Outcome: Concluído — `ruff check src tests` e `ty check` ambos verdes

## Baseline

- Tests: 559 passed, 34 skipped
- Branch coverage: 89.29% (gate `fail_under=85`)
- Failures: 0
- Skipped: 34 (triados — ver histórico abaixo)

## Completed objectives

- `migracao-ty/04` (fatia `ty`, fecha o ticket): os 150 diagnósticos do `ty check` foram a zero. 11 dos 32 `# type: ignore` legados eram mortos sob o `ty` — comentário removido. 3 sites de dívida real em `src` corrigidos sem supressão: `engine/discovery.py` (`cast` para o `Literal`), `cli/consolidate.py` (`cast(dict[str, object], ...)` — `dict` é invariante, `dict[str,str]` não é subtipo), `excel/capa.py` (migrado para `ty: ignore` com a justificativa já existente no código — stub de `Cell.value` mais estreito que o runtime do openpyxl). 18 sites em `tests/` migrados para `# ty: ignore[<rule>]` — todos testes deliberados de erro de runtime (`**kwargs` mal-tipados, atribuição em pydantic frozen, subscript em `Mapping` read-only); os 8 sites de `write_sheet(**kwargs)` em `test_inms_1_1_audit.py` cobrem sozinhos 12–14 diagnósticos de overload cada com um único comentário. 11 diagnósticos novos de ruído de stub `types-openpyxl` (`cell.row: int | None`) resolvidos com `assert <row> is not None` logo após o `next(...)` que deriva a linha — nunca é `None` em runtime (o teste já filtrou por um marcador antes de ler `.row`) — em vez de suprimir. `uv run ty check` → All checks passed em `src`+`tests`. Únicos diffs de produção são os 2 `cast()` (no-op em runtime, sem mudança de comportamento).
- `migracao-ty/03`: formalizada a resolução do ticket — a config já estava em `pyproject.toml` (perfil `ty` sem overrides de regra, escopo `include=[src,tests]`/`exclude=[.scratch]`, `respect-type-ignore-comments=false`, `ANN`/`PYI`+`preview` no ruff, `basedpyright` já removido) desde um commit `wip` anterior, nunca formalizada por escrito.
- `migracao-ty/04` (fatia `ruff check`): zerados os 18 erros pré-existentes por refactor mecânico, sem mudança de comportamento — `RUF067` (`SHAPE_REGISTRY`/`main()`/`run_interactive()` saíram de `__init__.py` para módulos próprios com re-export), `N818` (`InteractionCancelled`→`InteractionCancelledError`, `RunStateCorrupted`→`RunStateCorruptedError`, rename mecânico em 33 sites), `E501` (rewrap), `RUF001`/`002`/`003` (2 casos cosméticos em prosa corrigidos; 4 casos em fixtures de teste deliberadamente "ambíguas" — mojibake CSV, apóstrofo curvo de round-trip cp1252 — preservados verbatim e suprimidos via `ruff: ignore`/per-file-ignore documentado, nunca alterados), `RUF059`/`RUF105`/`SIM113` (autofix). `uv run ruff check src tests` → All checks passed.
- Triagem dos 34 skips: todos são `skipif` sobre a ausência local de dados reais de produção (`input/2026/06/…`), usados pelos testes de aceitação/smoke que validam o engine contra CSVs reais de competência (`tests/test_full_acceptance_smoke.py` e os 6 testes por shape irmãos, ver spec.md §5). Nenhum órfão, nenhum a reativar/converter/remover.
- `suite-testes/03`: reparo das ~90 costuras de string acidentais introduzidas pelo refactor em andamento. Suíte foi de 16 failed/543 passed para 559 passed/34 skipped.
- `suite-testes/02`: gate anti-regressão `ISC001`+`ISC003` no `[tool.ruff.lint]`. 0 hits, sem `per-file-ignores`.

## Known risks

- `bandit -r src` reporta 3 findings pré-existentes (B404/B603/B607, uso de `subprocess`) — fora de escopo, não relacionado a testes/tipagem.
- `ruff format --check` reporta 2 arquivos pré-existentes fora do `quote-style = single` (`ratio.py`, `workbook.py`) — não tocados em nenhuma rodada, fora do escopo de `ruff check`/`ty check`.
- Cobertura branch 89% está acima do gate (85%) mas não foi auditada por risco. Módulos com branch coverage mais baixo: `interactive/provider.py` (56%, fronteira Questionary), `log_json_sink.py` (70%), `orchestration/summary.py` (79%), `periodo.py` (79%), `orchestration/summary_json.py` (80%).

## Recommended next objective

Cobrir os branches de maior risco em `orchestration/summary.py` (79% branch, lógica central de composição do relatório de conformidade) e `orchestration/state.py` (82%) com testes de unidade/integração focados. O wayfinder `migracao-ty` está fechado (tickets 03/04); resta o ticket 05 (docs vivas de basedpyright → ty), não urgente.
