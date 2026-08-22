# 06 — Análise SRP do pacote orchestration

Type: research
Status: resolved
Blocked by: —

## Question

Analisar o pacote `src/pyauditor/orchestration/` (run.py 1109, summary.py 954, state.py 653) + módulos de raiz vinculados `logging.py` (infra de logging usada por todos) e `capa_paths.py` (resolução de caminhos de capa) com lente de SRP: run.py como o maior arquivo do projeto (1109) — coordenador de pipeline completo?; summary.py como gerador de relatório complexo; state.py como estado de execução/persistência. Procurar mistura orquestração+infra+persistência, efeitos colaterais globais prejudicando teste. Onde logging.py (783 linhas) acumula várias responsabilidades (log humano, formatação, sink, bridge loguru).

## Answer

Candidatos (detalhe em `.scratch/app-audit/notes/pacote-orchestration.md`):

- **CRÍTICA — `orchestration/run.py` (1109)** — coordenador de pipeline completo: topologia do plano, dispatch dos 5 comandos `cli.*`, verificação de artefatos por comando e recuperação de estado no mesmo arquivo. `execute_run` é God Function (293 linhas, cc≈22) e `_dispatch` (114) conhece todos os contratos; importa `_SINTETICO_FILENAME` privado de `cli.split:53`. 5 mocks de teste apontam para `run.run_measure`. Plano: `plan.py` (topologia), `command_dispatch.py` (dispatch+dependências+artefatos), `resume.py` (recuperação); API pública preservada via `__all__`.
- **ALTA — `logging.py` (784)** — 5 responsabilidades: política de severidade, contrato de evento, serialização JSON (`_normalize_json_value` cc≈18, sem cobertura), sink JSON (`_FlatJsonSink`) e bridge/setup do loguru global (`setup_logging` 157 linhas/cc≈11). Plano: `log_contract.py` + `log_json_sink.py`; consumido por 9 módulos mas via apenas 5 símbolos públicos.
- **ALTA — `orchestration/summary.py` (954)** — dois mundos: modelagem JSON/telemetria (`summary_json`) vs renderização Rich (`_result_panel` 116 linhas/cc≈12), além de exit-code de negócio e `fmt_pt_br`. Duplicações com `cli/results.py:98-109` (precedência 1>4>3>0) e `interactive/flow.py:66-72` (`_STATE_PRESENTATION`). Plano: `summary_json.py`.
- **MÉDIA — `orchestration/state.py` (653)** — grande porém coeso (schema de estado); dividir validadores seria fragmentação sem ganho de SRP. Não dividir.
- **NÃO RECOMENDADA — `capa_paths.py` (27)** — falso positivo; 1 função coesa que resolveu duplicação real.

Validações: `pytest` 506 passed/34 skipped; `mypy` Success; cobertura run.py 84%, summary 78%, state 82%, logging 62%, capa_paths 71%. `radon`/`xenon` indisponíveis — CC estimada via `ast`.