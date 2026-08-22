# Nota SRP — pacote orchestration (+ logging.py, capa_paths.py)

Escopo do ticket 06. Análise estática (`ast`; `radon`/`xenon` não instalados — limitação registrada no final).
Validações executadas: `pytest` 506 passed / 34 skipped; `mypy` Success; cobertura por módulo abaixo; `ruff`
só reporta 47 avisos pré-existentes de estilo (E501/W292) nos arquivos analisados, sem relação com SRP.

## 1. Resumo executivo

Arquivos analisados: 6 (`run.py`, `state.py`, `summary.py`, `__init__.py`, `logging.py`, `capa_paths.py`).

| Arquivo | Físicas | Lógicas* | Classes | Funções | Imports | Cobertura† |
|---|---|---|---|---|---|---|
| `orchestration/run.py` | 1109 | ~920 | 2 | 24 | 20 | 84% |
| `orchestration/summary.py` | 954 | ~759 | 5 (TypedDicts) | 24 | 20 | 78% |
| `logging.py` | 784 | ~632 | 2 | 18 | 14 | 62% |
| `orchestration/state.py` | 653 | ~521 | 3 | 20 | 8 | 82% |
| `capa_paths.py` | 27 | ~20 | 0 | 1 | 3 | 71% |
| `orchestration/__init__.py` | 0 | 0 | — | — | — | — |

*Linhas lógicas = físicas − vazias − comentários. †Cobertura branch da suite completa (506 tests), via `.coverage`.

Candidatos por prioridade: **CRÍTICA** = `run.py`; **ALTA** = `logging.py`, `summary.py`; **MÉDIA** = `state.py`
(grande, porém coeso — divisão não recomendada); **NÃO RECOMENDADA** = `capa_paths.py` (falso positivo) e `__init__.py`.

Riscos arquiteturais principais: (1) `run.py` como coordenador de pipeline completo — orquestração, dispatch de todos
os 5 comandos `cli.*`, verificação de artefatos de cada comando e recuperação de estado no mesmo arquivo; (2)
`execute_run` como God Function de 293 linhas/cc 22; (3) `summary.py` com dois mundos (modelagem JSON + renderização
Rich) e regra de negócio de exit-code duplicada; (4) `logging.py` com 5 responsabilidades distintas e menor cobertura
(62%) justamente no código mais complexo.

## 2. Ranking dos candidatos

### 2.1 `src/pyauditor/orchestration/run.py` — CRÍTICA

Maior arquivo do projeto (1109 físicas / ~920 lógicas). Confiança: **alta**.

Classes/funções relevantes: `RunRequest` (L139-172), `RunResult` (L175-199), `execute_run` (L817-1109, 293 linhas,
cc≈22, maior CC do arquivo), `_dispatch` (L566-679, 114 linhas), `record_failure_and_decide` (closure L891-949,
59 linhas), `_ensure_state` (L395-451), `_reconcile_state` (L342-392), `dependency_missing` (L468-514),
`_own_artifact_missing` (L517-563), `_cascade_skip` (L770-814), `_downstream` (L682-706), `_validate_request`
(L230-270), `_upsert` (L310-339), `_plan` (L273-294).

Responsabilidades identificadas (cada uma com motivo independente de mudança):

1. **Topologia do pipeline phase-major** — `_plan`, `_PHASE_ORDER` (L126-132), `_PHASE_INDEX` (L133),
   `_SUPPORTED_ORGAO_SELECTORS` (L111-117), `_ALL_COMMANDS` (L94-102). Motivo: adicionar/remover fase ou comando.
2. **Validação de request** — `_validate_request` (L230-270). Motivo: contrato de entrada (`orgao`, `commands`,
   `competencia`).
3. **Recuperação/reconciliação de estado persistido** — `_ensure_state`, `_reconcile_state`, uso de
   `reset_stale_running`/`RunStateCorrupted`/`state_path`. Motivo: schema de persistência e política de resume.
4. **Resolução de dependências pré-dispatch** — `dependency_missing` (L468-514), acoplado a `CHECKERS`
   (`cli.dependencies`, L45) e aos checkers de report/consolidate. Motivo: regras de pré-condição por comando.
5. **Verificação de artefato próprio** — `_own_artifact_missing` (L517-563): conhece o layout de arquivos de
   bootstrap/split/measure (capa, sintético, diretório de ROMs). Motivo: mudança de layout de saída de um comando.
6. **Dispatch de comando** — `_dispatch` (L566-679): converte `RunRequest` em chamadas `run_bootstrap`/`run_split`/
   `run_measure`/`run_report`/`run_consolidate` + `per_orgao_paths`. Motivo: mudança de contrato de qualquer comando.
7. **Máquina de decisão de falha** — `execute_run`, `record_failure_and_decide`, `_cascade_skip`, `_downstream`,
   `_validate_failure_decision` (L727-739), `_sanitize_error_message` (L709-724). Motivo: política retry/skip/
   isolate/abort e mensagens persistidas.
8. **Relógio** — `_now` (L225-227), não injetável; dificulta testes determinísticos (hipótese, sem evidência de falha
   real).

Sinais quantitativos: >800 linhas (candidato prioritário); `execute_run` 293 linhas e cc≈22 (limiar 40/10);
`_dispatch` 114 linhas; 20 imports; 2 funções públicas novas por comando tocariam 6+ pontos do arquivo (fato).

Sinais qualitativos: `execute_run` coordena e também executa detalhes de infraestrutura (persistir, decidir, dispatch);
`_dispatch` seleciona comportamento por comando com `if` encadeado (L581-679) e conhece os contratos de todos os
5 comandos; importa `_SINTETICO_FILENAME` privado de `cli.split` (L53) — acoplamento com símbolo privado (fato);
mistura domínio (`periodo`, L71), infraestrutura (paths, filenames L58-60) e interface de comandos `cli.*`.

Dependências: `cli.bootstrap/consolidate/dependencies/measure/report/split`, `config.resolution.per_orgao_paths`,
`excel.*` (nomes de arquivo), `periodo`, `logging`, `orchestration.state`, `capa_paths`.

Risco da refatoração: **alto** — é o núcleo usado por `cli/run.py:26`, `interactive/flow.py:34-38`,
`interactive/provider.py:41`, `summary.py:46-49` e patcheado por 5 mocks de teste
(`pyauditor.orchestration.run.run_measure`: `tests/test_orchestration_run.py:328,409,419,433` e
`tests/test_config_resolution.py:140`). Mover `_dispatch` muda o namespace onde `run_measure` é resolvido nos mocks.

Benefício esperado: separar os 4 motivos de mudança; tornar `execute_run` legível; permitir evoluir topologia,
dispatch e resume independentemente; reduzir o raio de impacto de mudanças de contrato de comando.

### 2.2 `src/pyauditor/logging.py` — ALTA

784 físicas / ~632 lógicas. Confiança: **alta**.

Classes/funções: `setup_logging` (L254-410, 157 linhas, cc≈11, 7 params), `log_event` (L184-251, 68 linhas),
`resolve_log_level` (L135-181), `LoggingHandlers` (L122-132), `_FlatJsonSink` (L413-482, `write` L426-482),
`_normalize_json_value` (L653-719, cc≈18), `_normalize_context` (L609-650), `_build_detail_filter` (L485-506),
validadores `_normalize_level`/`_validate_*` (L509-606, L769-784).

Responsabilidades (motivos independentes de mudança):

1. **Política de severidade/verbosity** — `resolve_log_level`, `_validate_verbosity`, `_normalize_level`,
   `_validate_detail`. Motivo: mudar precedência `explicit > -v > default`.
2. **Contrato de evento de auditoria** — `log_event`, `_validate_event`, `_validate_single_line_text`,
   `_normalize_context`, `_RESERVED_CONTEXT_KEYS` (L96-104), `_SENSITIVE_KEY_FRAGMENTS` (L106-115). Motivo: mudar o
   schema do evento (`event`/`detail`/contexto) ou a política anti-secret.
3. **Serialização JSON pura** — `_normalize_json_value` (cc≈18), `_format_text_value` (L722-735). Motivo: suportar
   novos tipos (Decimal, Path, Enum, Mapping).
4. **Adapter de sink JSON** — `_FlatJsonSink`, `_format_timestamp` (L738-751), `_format_level` (L754-766). Motivo:
   mudar o formato de saída JSON (flat, `separators`, schema de campos).
5. **Bridge/setup do loguru global** — `setup_logging`, `_build_detail_filter`, `_validate_sink`, `logger.remove()/
   add()` (L345-397). Motivo: troca de biblioteca de logging, política de retention/rotação, rollback de handlers.

Sinais quantitativos: 784 linhas; `setup_logging` 157 linhas / cc≈11 / 7 params; `_normalize_json_value` cc≈18;
14 imports; cobertura 62% — a menor do pacote — com ramos críticos descobertos (`_normalize_json_value` L658-716,
`sink` e caminhos de erro de `setup_logging` L388-405).

Sinais qualitativos: cada bloco do arquivo muda por um motivo diferente; `_FlatJsonSink` é um adapter de saída que
depende da serialização (`_normalize_json_value`) e dos validadores de evento (`_validate_event` L462),
evidenciando 3 camadas distintas num único módulo.

Dependências: `loguru` (import direto do singleton global, L56); consumido por 9 módulos — `engine/pipeline.py:22`,
`orchestration/run.py:61`, `cli/report.py:26`, `cli/bootstrap.py:29`, `cli/main.py:36` (setup, em 5 dispatchs),
`cli/consolidate.py:27`, `cli/measure.py:55`, `cli/split.py:46`, `excel/consolidate.py:50`.

Risco da refatoração: **médio** — API pública pequena e estável (`__all__` L58-64: `LoggingHandlers`, `log_event`,
`logger`, `resolve_log_level`, `setup_logging`); consumidores usam apenas estes 5 símbolos. Risco principal é
introduzir ciclo de import entre `logging.py` e os módulos extraídos (o sink usa validadores de evento).

Benefício esperado: isolamento da bridge loguru (para eventual troca de biblioteca), contrato de evento testável
sem handlers globais, e serialização reutilizável.

### 2.3 `src/pyauditor/orchestration/summary.py` — ALTA

954 físicas / ~759 lógicas. Confiança: **alta**.

Classes/funções: 5 TypedDicts (L98-143), `exit_code_for_run` (L146-183), `summary_json` (L642-694),
`render_summary` (L877-954, 78 linhas), `_result_panel` (L697-812, 116 linhas, cc≈12), `_command_table` (L815-853),
`fmt_pt_br` (L542-598, cc≈11), `_organization_summary` (L326-377), `_next_steps` (L601-639), `_result_for`
(L186-228), helpers de leitura (`_artifact_paths` L444-472, `_duration_ms` L514-539, `_warnings_count` L475-487,
`_errors_count` L490-492).

Responsabilidades:

1. **Regra de negócio de exit-code agregado** — `exit_code_for_run` (precedência 1>4>3>0, L168-182).
2. **Modelagem do relatório estruturado (JSON/telemetria)** — `summary_json` + TypedDicts + `_organization_summary`,
   `_consolidated_info` (L420-441), `_json_number` (L380-417), `_duration_ms`, `_warnings_count`, `_errors_count`,
   `_artifact_paths`, `_orgaos_no_run` (L309-323), `_result_for`.
3. **Apresentação Rich (texto)** — `render_summary`, `_result_panel`, `_command_table`, `_lines_panel` (L856-874),
   `_artifact_line` (L277-306), `_STATE_PRESENTATION` (L69-75).
4. **Localização numérica pt-BR** — `fmt_pt_br` (função pública, usada em `_result_panel` L765 e L773-777).
5. **Recuperação acionável ("Próximos passos")** — `_next_steps`, que reutiliza `dependency_missing` de `run.py`.

Sinais quantitativos: 954 linhas; `_result_panel` 116 linhas/cc≈12; `fmt_pt_br` cc≈11; 20 imports; cobertura 78%,
com os ramos de formatação/erro descobertos (L401-417, L566-596, L914-926).

Sinais qualitativos: dois mundos no mesmo arquivo — construção de dados (máquina) e renderização Rich (humano) —
compartilham os mesmos helpers de leitura; duplicação observada: precedência de exit-code também existe em
`cli/results.py:exit_code_for_results` (L98-109); `_STATE_PRESENTATION` é idêntico a `interactive/flow.py:66-72`;
`_parse_run_timestamp` (L495-511) repete a normalização de `Z` de `state.py:_parse_optional_timestamp` (L550).

Dependências: `rich.*`, `cli.results` (exit_code_name/is_production_command, L44), `cli.*` (tipos de Result),
`orchestration.run` (RunResult, dependency_missing, L46-49), `orchestration.state` (L50-53).

Risco da refatoração: **médio** — consumidores `cli/run.py:27` e `interactive/provider.py:42-45` usam apenas
`OutputFormat`, `exit_code_for_run`, `render_summary`; `summary_json` é usado em teste (L157) e via `render_summary`.
Risco: separar model/render exige decidir onde fica `exit_code_for_run` (negócio, não apresentação).

Benefício esperado: testar o schema JSON sem depender de Rich/console; reusar `_organization_summary` sem acoplar a
estilos; reduzir `_result_panel` a composição de blocos.

### 2.4 `src/pyauditor/orchestration/state.py` — MÉDIA (divisão não recomendada)

653 físicas / ~521 lógicas. Confiança: **média**.

Classes/funções: `RunStateCorrupted` (L90-111), `CommandStateEntry` (L114-148), `RunState` (L151-163),
`state_path` (L166-195), `load_state` (L198-229), `save_state` (L232-268), `reset_stale_running` (L271-304),
`_decode_state` (L307-349), `_decode_command` (L352-397), `_validate_state` (L400-426),
`_validate_command_entry` (L429-511, 83 linhas, cc≈10), validadores `_require_*`/`_validate_*` (L514-653).

Responsabilidades: modelo de domínio do estado, endereçamento do arquivo (`state_path` com segurança de nome),
persistência atômica (JSON via `atomic_write`), decodificação/validação de schema versionado, invariantes de
ciclo de vida (pending/running/done/skipped/error).

Sinais quantitativos: 653 linhas; `_validate_command_entry` 83 linhas/cc≈10; cobertura 82%; 8 imports (baixo).

Sinais qualitativos: coeso — todos os símbolos mudam por um mesmo motivo central (o schema do documento persistido).
A separação dos validadores (`_require_*`, `_decode_*`) seria divisão por tamanho, sem motivo independente de mudança
(spec item 5 do Processo: "Não proponha divisões artificiais baseadas somente em quantidade de linhas"). `_validate_
command_entry` é candidata a simplificação interna (hipótese), não a novo módulo.

Dependências: apenas `pyauditor.atomic_write` (L31); consumido por `run.py:62`, `summary.py:50`,
`interactive/flow.py:39` e testes.

Risco/benefício: divisão de módulo tem benefício baixo e risco de fragmentação; **não recomendada** a divisão.
Melhoria interna opcional (BAIXA): extrair o núcleo de validação de ciclo de vida para reduzir CC.

### 2.5 `src/pyauditor/capa_paths.py` — NÃO RECOMENDADA (falso positivo)

27 físicas / ~20 lógicas, 1 função pública `resolve_capa_path` (L16-27). Criado (docstring L1-6) para unificar
`_capa_path_for` duplicado e divergente entre `cli/main.py` e `orchestration/run.py` — resolveu um problema real de
duplicação. Alto valor por baixa complexidade. Cobertura 71%. Confiança: **alta**. Não dividir.

### 2.6 `src/pyauditor/orchestration/__init__.py` — NÃO RECOMENDADA

Vazio (0 linhas). Não é problema.

## 3. Plano sugerido por arquivo

### run.py (CRÍTICA) — ordem segura

Novos módulos dentro de `src/pyauditor/orchestration/`:

1. `plan.py` — topologia do pipeline (extração pura, zero efeito colateral):
   - mover: `PlanStep`, `_ALL_COMMANDS`, `_ORGANIZATION_COMMANDS`, `_SUPPORTED_ORGAO_SELECTORS`, `_PHASE_ORDER`,
     `_PHASE_INDEX`, `_plan` (L273-294), `_downstream` (L682-706), e `ResultKey`/`_result_key` (L742-747) se desejado.
   - permanece em run.py: nada da topologia.
2. `command_dispatch.py` — adapter plano→execução:
   - mover: `_dispatch` (L566-679), `dependency_missing` (L468-514), `_own_artifact_missing` (L517-563).
   - esse módulo concentra o acoplamento a `cli.*`/`config.resolution`/`excel.*`/`capa_paths`.
3. `resume.py` — recuperação de estado:
   - mover: `_ensure_state` (L395-451), `_reconcile_state` (L342-392). Depende de `state.*` e de `plan.PlanStep`.

run.py mantém: `RunRequest`, `RunResult`, `FailureDecision`, `execute_run`, closures `finish_result`/
`record_failure_and_decide`, `_cascade_skip`, `_find_entry`/`_upsert`, `_validate_request`,
`_validate_failure_decision`, `_sanitize_error_message`, callbacks públicos (`isolate_on_failure` etc.), `_now`.

API preservada: `__all__` inalterado; run.py re-exporta `dependency_missing` de `command_dispatch` (e `PlanStep`
se fizer parte de contrato). `summary.py:46-49`, `cli/run.py:26`, `interactive/*` seguem importando do mesmo lugar.

Testes antes: suite atual 41 testes verdes (fato). Acrescentar antes da extração: testes unitários diretos de
`_dispatch` (já existe cobertura indireta via `execute_run`), de `dependency_missing` por comando (parcial hoje,
cobertura L496-512), e de `_own_artifact_missing`. Testes depois: atualizar os 5 patches de
`pyauditor.orchestration.run.run_measure` para o novo namespace `command_dispatch` — ou, para reduzir o diff, manter
um alias em run.py (não recomendado: mascara o novo limite).

### logging.py (ALTA) — ordem segura

Novos módulos de raiz `src/pyauditor/`:

1. `log_contract.py` — contrato e serialização (sem loguru, sem sinks):
   - mover: `_normalize_json_value`, `_format_text_value`, `_normalize_context`, `_validate_event`,
     `_validate_single_line_text`, `_validate_detail`, `_validate_verbosity`? (verbosity é política — fica), e as
     constantes `_EVENT_RE`, `_CONTEXT_KEY_RE`, `_RESERVED_CONTEXT_KEYS`, `_SENSITIVE_KEY_FRAGMENTS`,
     `_DEFAULT_DETAIL_LEVEL`, `_MAX_DETAIL_LEVEL`, `_SUPPORTED_LEVELS`/`_normalize_level` (usados pelo sink).
   - isso elimina o risco de ciclo (sink usa apenas `log_contract`).
2. `log_json_sink.py` — adapter loguru→JSON:
   - mover: `_FlatJsonSink`, `_format_timestamp`, `_format_level`.

logging.py mantém: `logger`, `log_event`, `resolve_log_level`, `setup_logging`, `LoggingHandlers`,
`_build_detail_filter`, `_validate_sink`, `_validate_verbosity`, `_normalize_level`. API pública inalterada
(`__all__`).

Testes antes: ampliar `tests/test_logging.py` (88 linhas, baixa cobertura 62%): `_normalize_json_value` (Decimal,
datetime naive, dataclass, Enum, Mapping aninhado), caminhos de erro de `setup_logging` (rollback, json sink com
Path, `log_path` inválido). Testes depois: mesma suite, agora cobrindo os módulos novos; verificar que
`logger is loguru_logger` e os 5 exports seguem passando.

### summary.py (ALTA) — ordem segura

Novo módulo `orchestration/summary_json.py` — modelagem do relatório:
- mover: `summary_json` (L642-694), os 5 TypedDicts (L98-143), `_organization_summary`, `_consolidated_info`,
  `_json_number`, `_warnings_count`, `_errors_count`, `_duration_ms`, `_artifact_paths`, `_orgaos_no_run`,
  `_result_for`, `_parse_run_timestamp`.

summary.py mantém: `render_summary`, `_result_panel`, `_command_table`, `_lines_panel`, `_artifact_line`,
`_STATE_PRESENTATION`, `fmt_pt_br`, `exit_code_for_run`, `_next_steps`.

Decisão: `exit_code_for_run` fica em summary.py (negócio de agregação do run); **não** movê-lo para
`cli/results.py` — inverteria a direção de dependência (cli passaria a importar `orchestration.state`). Opção
futura: deduplicar a precedência 1>4>3>0 com `cli/results.py:exit_code_for_results` via um helper compartilhado
em camada neutra (ex.: `cli/results.py` mantido, resumo chama um `_exit_code_from_flags`), avaliar em ticket de
síntese. API preservada via re-export de `summary_json`.

Testes antes: `tests/test_orchestration_summary.py` (236 linhas) já cobre JSON via `render_summary`; adicionar teste
direto de `summary_json` isolado do console antes da extração. Testes depois: suite completa + teste do schema JSON
(TypedDict) sem depender de Rich.

### state.py (MÉDIA) — sem divisão

Nenhuma extração de módulo. Melhoria interna opcional (BAIXA, fora do escopo de divisão): reduzir a CC de
`_validate_command_entry` (L429-511) extraindo o núcleo de invariantes por status. Não recomendado mover os
validadores para módulo próprio.

## 4. Falsos positivos e arquivos grandes aceitáveis

- `capa_paths.py` (27 linhas): pequeno, coeso, resolveu duplicação real; não dividir.
- `state.py` (653 linhas): grande porém coeso em torno do schema de estado; dividir os validadores seria
  fragmentação sem ganho de SRP.
- `orchestration/__init__.py`: vazio; normal.
- `interactive/flow.py:66-72` e `summary.py:69-75`: `_STATE_PRESENTATION` duplicado — remoção de duplicação é
  recomendada como etapa de melhoria, mas não justifica divisão de arquivo.

## 5. Plano incremental

1. **Testes** (antes de qualquer extração): fortalecer `test_logging.py` (62%) e testes diretos de `_dispatch`/
   `dependency_missing`; adicionar teste isolado de `summary_json`.
2. **Extração sem mudança de comportamento**: `log_contract.py` + `log_json_sink.py`; `plan.py` (puro).
3. **Redução de dependências**: mover `_dispatch`/`dependency_missing`/`_own_artifact_missing` para
   `command_dispatch.py` (atualiza 5 patches de mock); mover recuperação para `resume.py` (opcional).
4. **Divisão de módulo**: `summary_json.py`.
5. **Melhoria de nomes/APIs**: manter `__all__`; avaliar deduplicação da precedência de exit-code e de
   `_STATE_PRESENTATION`/`_parse_run_timestamp`.
6. **Remoção de duplicações**: precedência 1>4>3>0, `_STATE_PRESENTATION`, parse de timestamp Z.

## 6. Validações recomendadas

Após cada etapa (mesmas ferramentas do repo):

- `.venv/bin/python -m pytest tests -q` (506 expected pass)
- `.venv/bin/python -m mypy src tests`
- `.venv/bin/python -m ruff check src tests`
- `.venv/bin/python -m pytest tests -q --cov=pyauditor --cov-branch` (gate 85%)

## Limitações

- `radon`/`xenon` não instalados (map.md): complexidade ciclomática foi estimada com `ast` (soma de
  `If`/`While`/`For`/`AsyncFor`/`BoolOp`), portanto **aproximada** — pode subestimar `match`/`except`/short-circuit.
- Cobertura por módulo reflete a suite completa executada nesta sessão (506 passed / 34 skipped); o `.coverage`
  presente no repo, isolado, mostrou números menores (16% agregado nos 5 módulos) e foi desconsiderado por ser
  parcial.
- Contagem lógica é estimativa (físicas − vazias − comentários).

## Fato observado vs. hipótese

- **Fato**: contagens, CC via `ast`, cobertura, `mypy` Success, `pytest` 506/34, 47 avisos E501/W292 do `ruff`.
- **Fato**: `run.py` importa `_SINTETICO_FILENAME` privado (L53); `summary.py` importa de `run.py` (L46-49);
  precedência de exit-code duplicada (`summary.py:168-182` vs `cli/results.py:98-109`); `_STATE_PRESENTATION`
  duplicado (`summary.py:69-75` vs `interactive/flow.py:66-72`); parse de timestamp Z duplicado
  (`summary.py:495-511` vs `state.py:539-560`); 5 mocks apontam para `pyauditor.orchestration.run.run_measure`;
  `logging.py` consumido por 9 módulos; `setup_logging` chamado em 5 dispatchs de `cli/main.py`.
- **Hipótese**: `_dispatch` como "adapter de comandos" e `execute_run` como God Function — leitura arquitetural,
  sem teste isolado que a prove; `_now` não injetável dificultando determinismo — suposição de design, sem evidência
  de falha; separação `summary` em JSON/render reduz acoplamento a Rich — por validar com o plano de testes.