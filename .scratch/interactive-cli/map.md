# Map: CLI interativa guiada

Label: wayfinder:map

## Destination

Um spec de design aprovado para a experiência de CLI interativa do pyauditor: a arquitetura de separação entre a camada de pipeline (serviços/casos de uso já existentes — `run_bootstrap`/`run_measure`/`run_report`/`run_consolidate`) e a camada de apresentação/interação, a máquina de estados de execução (Command state: pending/running/done/skipped/error), o fluxo de UX guiado (onboarding, entrada progressiva validada com defaults/voltar/revisar, ajuda contextual), a resumibilidade (decidida diretamente — persistência de estado de run), o tratamento de falhas (retry/skip/abort, contexto preservado) e o resumo final + código de saída. Pronto para virar tickets de implementação — este mapa não implementa.

Os 4 comandos existentes (`bootstrap`, `measure`, `report`, `consolidate`) e seus contratos `Request` (`MeasureRequest`/`ReportRequest`/`ConsolidateRequest`) são **entradas fixas** — fora de escopo redesenhá-los.

## Notes

- Domínio: pyauditor — ver `CONTEXT.md`. Este mapa é sobre a camada de CLI, não sobre o domínio de aferição/glosa.
- Skills que toda sessão deve consultar: `grilling` e `domain-modeling` (default); `prototype` para tickets de UX/comportamento.
- Vocabulário travado (não é termo de domínio de negócio — não vai para `CONTEXT.md`):
  - **Command**: um dos 4 subcomandos (`bootstrap`/`measure`/`report`/`consolidate`), como no código (`Command: TypeAlias` em `src/pyauditor/cli/main.py`).
  - **Request**: as dataclasses congeladas já existentes (`MeasureRequest` etc.) — fronteira entre parsing de CLI e execução de pipeline.
  - **Run**: uma invocação do fluxo (interativo ou `pyauditor run`), potencialmente encadeando múltiplos Commands, identificada por `(competencia, orgao)`.
  - **Command state**: pending/running/done/skipped/error, por Command dentro de um Run (sem `cancelled` separado — ticket "Failure-handling flow" decidiu que cascata de skip usa `skipped` também, distinção sem diferença de comportamento).
- Decisões de fundação aprovadas no grill breadth-first (Q1–Q9, 2026-08-19):
  - Fluxo guiado dispara **só** em `pyauditor` sem argumento nenhum; comando nomeado com args faltando mantém o erro normal do argparse.
  - Nova package irmã `src/pyauditor/interactive/` (nome exato a definir no ticket de arquitetura), dependência de mão única (`interactive/` → `cli/`/orquestração; nunca o inverso).
  - Novo comando não-interativo `pyauditor run <competencia>` (nome exato a definir) orquestra bootstrap→measure→report→consolidate em uma invocação scriptável — orquestração não fica só na camada interativa.
  - Resume: arquivo de estado JSON por run (ex.: `.pyauditor/runs/<competencia>-<orgao>.json`), granularidade por Command (nunca no meio de um Command).
  - A cadeia de dependência bootstrap→measure→report→consolidate passa a ser validada pela camada de orquestração compartilhada, para os dois modos (hoje é só convenção).
  - Progresso/feedback: `rich.Progress`/spinners em torno de chamadas síncronas — sem asyncio/threading (operações são openpyxl/pandas em processo único, não I/O de rede).
  - Biblioteca de prompt: adicionar `questionary` (multi-select/checkbox para seleção de Commands); `argparse` continua sendo a camada não-interativa (sem migrar para `click`/`typer`).
  - Camada interativa desenhada em torno de um protocolo injetável de prompt/output desde o início — testável sem TTY real.
  - `run_bootstrap`/`run_measure`/`run_report`/`run_consolidate` já são livres de apresentação (só `loguru`, nunca `print`/rich), mas retornam só `int` — trocar para um dataclass de resultado estruturado (mirroring `Request`) em vez de reconstruir o resumo relendo arquivos de saída.
- Plan, don't do: este mapa resolve decisões de design; a implementação fica para depois (handoff).

## Decisions so far

- [Structured result dataclasses](issues/01-structured-result-dataclasses.md) — 4 independent frozen dataclasses (`BootstrapResult`/`MeasureResult`/`ReportResult`/`ConsolidateResult`, colocated per file, no shared base, mirrors `Request` pattern); `status: Literal["done","error"]` (`exit_code` derived via shared helper, never stored); `competencia`/`orgao` identity fields (no `orgao` on `ConsolidateResult`); `warnings: tuple[str,...]` + separate `error_message: str | None`; `MeasureResult.indicators: tuple[IndicatorOutcome,...]` per-indicator breakdown; `cli_main`'s `--orgao both` fan-out collects `list[...Result]` instead of `code |= run_measure(...)`.
- [Dependency enforcement](issues/02-dependency-enforcement.md) — filesystem is the source of truth (not run-state); thin registry `cli/dependencies.py` mapping Command → checker, logic colocated per command file; one checker function per Command (not a generic table — `report` needs bootstrap+measure, `consolidate` needs both órgãos), shared `DependencyCheck(satisfied, missing)` result; checker called both at dispatch (pre-flight, blocks invalid interactive selections) and inside each `run_*` (defense-in-depth for direct callers); no `--force` escape hatch; checked per-Command immediately before dispatch, never once at Run start.
- [Run orchestrator and resume](issues/03-run-orchestrator-and-resume.md) — `pyauditor run <competencia>` reuses today's flags/path-derivation as-is; `--orgao both` runs phase-major (bootstrap MinC+MTur, then measure MinC+MTur, then report MinC+MTur, then one `consolidate`); run-state file `.pyauditor/runs/<competencia>-<orgao-selector>.json`, minimal per-Command entries (full Command state, not the `Result` dataclasses), reused across attempts, never auto-deleted, no file locking; resume is automatic (no flag), stale `running` entries reset to `pending` and re-run from scratch; failure aborts the rest of the chain via the existing dependency check (no `--continue-on-error`), overall exit code `1` if any Command errored.
- [Interactive layer architecture](issues/04-interactive-layer-architecture.md) — orchestrator (the phase-major loop/run-state/dependency-checks designed in "Run orchestrator and resume") gets its own home: new sibling package `src/pyauditor/orchestration/` with `execute_run(request, on_state_change=...)`, called identically by `cli/run.py` (no-op callback) and by `interactive/` (its `InteractionProvider` as callback) — the single seam that keeps business logic unduplicated. `interactive/` = `provider.py` (single `InteractionProvider` Protocol + `RichQuestionaryProvider`) + `flow.py` (screen sequence) + `__init__.py` (`run_interactive()` entry point). Test double at `tests/support/fake_interaction_provider.py`. Non-TTY detection happens at the dispatch point (`cli_main`), before `interactive/` is even imported. `loguru` log file keeps writing silently in parallel — no live log panel.
- [Guided flow UX screens](issues/05-guided-flow-ux-screens.md) — runnable prototype (`rich`+`questionary`) at `.scratch/interactive-cli/prototype_guided_flow.py` on branch `prototype/interactive-cli-ux` (commit `4ba2df4`); validated screen shapes: opening panel + uniform `?`-for-help loop, inline-validated progressive input with a confirm-then-revise loop, `questionary.checkbox` command selection with invalid combos genuinely disabled (not just warned), live state table with symbol+color per Command state, error panel + retry/skip/abort chooser (semantics deferred to "Failure-handling flow"), summary table + artifacts panel + log path + next-steps panel + exit code (exact field contents deferred to "Completion summary and exit codes").
- [Failure-handling flow](issues/06-failure-handling-flow.md) — pre-dispatch dependency failures get a 2-option screen (skip/abort, no retry — nothing external changed); execution failures (`Result.status="error"`) get all 3. Retry re-executes the same `Request` from scratch, no inline editing (abort-and-reinvoke covers changed args). Skip cascades proactively to every transitively-dependent Command in the plan, one consolidated message. No `cancelled` Command state — skip covers both direct and cascaded cases. Resume (amends "Run orchestrator and resume") skips `done` *or* `skipped`, retries anything else. No message catalog — screens render `Result.error_message`/`DependencyCheck.missing` verbatim.
- [Completion summary and exit codes](issues/07-completion-summary-and-exit-codes.md) — new `RunResult` aggregate (in `orchestration/`) groups by órgão for `--orgao both`, shows per-Command artifacts/warnings/error, `measure` shows a count + only failing indicators (not all 14). "Próximos passos" computed live from the same dependency checkers (ticket "Dependency enforcement"), not a second static table. Exit code `1` iff any Command state is `error`; `skipped` never counts as failure. Summary rendering is one shared `orchestration/summary.py::render_summary()` using `rich.Console` directly, called by both `cli/run.py` and `interactive/`'s `show_summary` — no `InteractionProvider` indirection needed for pure output.

## Not yet specified

- Copy final (texto em português) dos prompts, mensagens de ajuda e erros — o protótipo já usa um tom e vocabulário consistentes com `cli/main.py`, mas não é copy final revisada; pode graduar em ticket próprio se a implementação achar necessário.

## Out of scope

- Redesenhar os contratos de argumento dos 4 comandos existentes (`bootstrap`/`measure`/`report`/`consolidate`) — fixados como fronteira do destino (grill de destino, Q2, 2026-08-19).
