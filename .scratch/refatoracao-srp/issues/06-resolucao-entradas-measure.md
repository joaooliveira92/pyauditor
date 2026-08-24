# 06 — Extrair resolução de entradas do measure

Type: task

**What to build:** as etapas de entrada de `run_measure` deixam de viver no corpo da função principal. Validação de competência, descoberta de configs, criação do diretório de saída, leitura de equipe/responsáveis, carregamento e expansão de `categorias.yaml` e derivação de stems de configs por categoria vão para um módulo próprio (`cli/measure/_inputs.py`); `run_measure` passa a orquestrar.

**Blocked by:** nenhum — pode começar imediatamente.

**Status:** resolved

- [x] `run_measure` reduzido a orquestração, com mesma assinatura pública.
- [x] Mensagens de warning/erro (equipe, categorias, janela vazia, `DIR_FAILURE_HINT`) inalteradas, verbatim.
- [x] Expansão de categorias em memória e supressão de configs derivadas (ADR 0002) preservadas.
- [x] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes (suíte `test_cli_measure.py` como rede).

## Contexto (do relatório SRP)

`cli/measure.py` (761 físicas, 20 imports) é o hub CRÍTICO do projeto: `run_measure` tem 580 linhas, com closures `_error`, `_hard_fail_todas_categorias` e `_handle_result` capturando estado mutável via `nonlocal`. Consumidores: `cli/main.py`, `cli/dependencies.py`, `orchestration/command_dispatch.py`, `orchestration/summary.py`, `orchestration/summary_json.py`, 3 arquivos de teste.

## Answer

Criado `src/pyauditor/cli/measure_inputs.py` (ticket 06 SRP; não usei `cli/measure/` porque `measure` já é um módulo, não pacote — o nome colide). Ele concentra toda a resolução de entradas de `run_measure`:

- `resolve_measure_inputs(competencia, config_dir, data_dir, output_dir, *, expected_orgao, equipe_path, manifest) -> tuple[MeasureInputs | None, str | None]` — valida competência, resolve o diretório `<data-dir>/<YYYY>/<MM>`, descobre configs, garante o `target_dir` (com `DIR_FAILURE_HINT` verbatim), e devolve as entradas agregadas.
- `MeasureInputs` (dataclass congelada): `orgao`, `competencia_data_dir`, `configs`, `target_dir`, `capa_fields`, `warnings`, `per_inms`, `derived_config_stems`, `categorias_file`.
- Helpers internos `_load_responsaveis`, `_load_categorias` (fallback `_shared` → parent/<órgão>), `_derived_config_stems` (ADR 0002) e `_inms_key_from_contractual_id` (usado pelo loop).

`cli/measure.py`: `run_measure` passou a chamar `resolve_measure_inputs` primeiro e usa os campos resolvidos; o bloco de entrada (validação de competência, descoberta de configs, criação de diretório, equipe/categorias/stems) saiu do corpo. Mensagens de erro/warning mantidas verbatim. Import `GrupoExecutorMode` continua usado nas anotações das closures de medição. A assinatura pública de `run_measure` (e seu `__all__`) inalterada.

Validação: `uv run pytest` 586 passados, cobertura 89.49% (gate 85% ok); `uv run ty check`, `uv run ruff check`, `uv run ruff format --check` e `uv run bandit` verdes. Suítes `test_cli_measure.py`, `test_multi_asset_discovery.py`, `test_measure.py` verdes sem alteração.