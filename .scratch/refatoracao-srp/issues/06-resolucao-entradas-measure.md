# 06 — Extrair resolução de entradas do measure

Type: task

**What to build:** as etapas de entrada de `run_measure` deixam de viver no corpo da função principal. Validação de competência, descoberta de configs, criação do diretório de saída, leitura de equipe/responsáveis, carregamento e expansão de `categorias.yaml` e derivação de stems de configs por categoria vão para um módulo próprio (`cli/measure/_inputs.py`); `run_measure` passa a orquestrar.

**Blocked by:** nenhum — pode começar imediatamente.

**Status:** ready-for-agent

- [ ] `run_measure` reduzido a orquestração, com mesma assinatura pública.
- [ ] Mensagens de warning/erro (equipe, categorias, janela vazia, `DIR_FAILURE_HINT`) inalteradas, verbatim.
- [ ] Expansão de categorias em memória e supressão de configs derivadas (ADR 0002) preservadas.
- [ ] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes (suíte `test_cli_measure.py` como rede).

## Contexto (do relatório SRP)

`cli/measure.py` (761 físicas, 20 imports) é o hub CRÍTICO do projeto: `run_measure` tem 580 linhas, com closures `_error`, `_hard_fail_todas_categorias` e `_handle_result` capturando estado mutável via `nonlocal`. Consumidores: `cli/main.py`, `cli/dependencies.py`, `orchestration/command_dispatch.py`, `orchestration/summary.py`, `orchestration/summary_json.py`, 3 arquivos de teste.