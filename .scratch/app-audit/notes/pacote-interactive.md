# Pacote `interactive` — auditoria SRP

Ticket: `.scratch/app-audit/issues/05-pacote-interactive.md`

Método: análise estática com `ast` (complexidade ciclomática simplificada, contagem de stmts); `ruff` 0.16.3, `mypy` 2.3.1 (strict), `pytest` 9.1.1. **Limitação**: `radon`/`xenon` não instalados — a CCM aqui é McCabe simples (If/For/While/Try/With/comp/not match) que *subestima* a de radon (ignora curto-circuito `and`/`or` em `BoolOp` é contado, mas não contagens de `except`, `elif`). Contador de "linhas de comentário" foi descartado (docstrings inflavam o número). Nenhum arquivo de código foi modificado.

## Visão geral

| Arquivo | Físico | Lógico (stmt) | Prioridade |
|---|---|---|---|
| `src/pyauditor/interactive/flow.py` | 559 | 140 | **ALTA** |
| `src/pyauditor/interactive/provider.py` | 436 | 123 | **MÉDIA** |
| `src/pyauditor/interactive/__init__.py` | 13 | 7 | NÃO RECOMENDADA |

Total: 1.008 linhas físicas / 270 stmts.

**Fato vs. hipótese do ticket**: o ticket previa "acoplamento com excel/config". **Não observado** — `grep` por `pyauditor.(excel|config|categor|engine)` no pacote não encontra nada; nenhum import do módulo `excel` nem `config` em `flow.py`/`provider.py`. O acoplamento real do pacote é com **orquestração/domínio**:

- `flow.py:30–33` + `flow.py:34–42` → `provider` + `orchestration.run`/`orchestration.state`;
- `flow.py:43` → `periodo.month_bounds` (usado só em validação);
- `provider.py:41–45` → `orchestration.run` (RunResult) e `orchestration.summary` (renderização/exit-code).

O design flow/provider já é uma separação SRP madura (UI atrás de `InteractionProvider` Protocol, orquestração via callbacks de `execute_run`). Não há God Object no pacote; as violações são de **nível de função** e de **acoplamento/triplicação de constantes de contrato**.

---

## 1. `flow.py` — ALTA

### Responsabilidades presentes

1. Orquestração do fluxo (`run_guided_flow`/`_run_guided_flow`, 457–559) — hmm, na verdade é UI/orquestração de telas: decide "próxima tela" e traduz escolhas do usuário em callbacks do orquestrador (`on_state_change`, `on_failure`, 508–552).
2. Especificação do formulário de coleta (7 campos, 206–315) com prompts, defaults, textos de ajuda, validações e transformações (ex.: `orgao_choice.startswith("both")` em 247; `Path(answer.strip()).expanduser()` em 193).
3. Validação (98–128: `_validate_competencia`, `_validate_non_empty_text`) — usa o parser de domínio `periodo.month_bounds` (109–117).
4. Catálogo e `seleção` de comandos (`_ALL_COMMANDS` 56–62; labels e opções em 341–371; loop de re-seleção 373–384).
5. Política de re-execução (`_force_commands_for`, 421–440: report/consolidate sempre forçados).
6. Apresentação de estado de transição (`_STATE_PRESENTATION` 66–72, `_state_presentation` 388–395, `_render_state_line` 398–418).
7. Discriminador de falha pré-dispatch (`_is_pre_dispatch_failure` 443–454) — baseado em prefixo mágico.

**Motivos independentes para mudar**: (a) mudar um campo do formulário; (b) mudar a política de comandos/forcíceo; (c) mudar a apresentação do estado (ícones/estilo); (d) mudar o contrato de frases do orquestrador (ex.: o prefixo); (e) traduzir `FailureDecision`. Cinco razões distintas para mexer no mesmo arquivo → sinal #2/#10/#11 do spec.

### Candidatos por função

| Candidato | Local | Fís | CCM | Prioridade |
|---|---|---|---|---|
| `collect_answers` | 206–315 | 110 | 2 | **ALTA** (função longa, `>70` de formulário) |
| `_run_guided_flow` + callbacks | 482–552 | 78 | 4 | **ALTA** |
| `select_commands` | 318–385 | 68 | 5 | **MÉDIA** |
| `_force_commands_for` | 421–440 | 20 | 3 | MÉDIA (política de negócio dentro de UI) |
| `_is_pre_dispatch_failure` | 443–454 | 12 | 1 | MÉDIA (acoplamento de string) |
| `_ask_with_help`/`_ask_path`/validators | 103–193 | 82 | 1–2 | coesos — manter |

**Evidências quantitativas**: arquivo 559 (>500 = candidato relevante); 110-stmt lógicos; funções que excedem 40 fís: `collect_answers`, `_run_guided_flow`, `select_commands` (68). **Qualitativas**: o formulário é codificado de forma imperativa — 7 repetições da estrutura "pergunta com `_ask_with_help`/`_ask_path`" com textos de ajuda embutidos; `select_commands` e `run_guided_flow` invocam `_force_commands_for` (421) e `_is_pre_dispatch_failure` (443), acoplando UI à política de orquestração.

### Plano de divisão (API pública preservada)

Mantêm-se públicos em `flow.py`: `GuidedAnswers`, `collect_answers`, `run_guided_flow`, `select_commands`, `show_opening` (`__all__` em 45–52) — nada muda para consumidores (só `cli/main.py:698–700`, TTY-gated, e os testes).

1. **`interactive/fields.py`** — modelo de formulário:
   - mover `_validate_competencia` (103–117), `_validate_non_empty_text` (120–128), `_ask_with_help` (131–158), `_ask_path` (161–193), e o *spec* dos 7 campos (prompts/defaults/help presentes em 222–303) para um `FieldSpec` (dataclass: `key`, `prompt`, `default`, `validator`, `help`) + função `collect_fields(provider, spec) -> dict[str, object]`;
   - `collect_answers` vira wrapper: `spec` → `collect_fields` → construir `GuidedAnswers` (mapeia chave→atributo) → loop de confirmação (304–313 permanece no flow, é sua responsabilidade).
   - API preservada, comportamento idêntico; testes existentes de `collect_answers` (test_interactive_flow.py:21, 41, 105) continuam válidos.

2. **`interactive/commands.py`** — catálogo e política de comandos:
   - mover `_ALL_COMMANDS` (56–62), labels de `select_commands` (341–347), opções disponíveis/disabled (350–368) e `_force_commands_for` (421–440);
   - `select_commands` fica no flow com apenas o loop de re-seleção quando vazio (370–384);
   - API: `select_commands(provider, orgao)` público mantido.

3. **`interactive/status_view.py`** — apresentação de transições (estado→ícone/estilo):
   - mover `_STATE_PRESENTATION` (66–77), `_state_presentation` (388–395), `_render_state_line` (398–418);
   - passo (recomendado quando o ticket de `orchestration` estiver disponível): deduplicar com `summary.py` (o mesmo mapeamento vive exatamente idêntico em `summary.py:69–80` e o `render_state_line` é quase o padrão das linhas da `_command_table` em `summary.py`).

4. **Não mover para este pacote**: `_is_pre_dispatch_failure` (acoplamento com `run.py`). A string `"dependência não satisfeita:"` é produzida em `run.py:1011` e consumida em `flow.py:64/443–454` — uma string mágica atravessando camadas. Correção definitiva requer expor `is_pre_dispatch_failure` canônico em `pyauditor.orchestration` (ou out.: estado com campo `failure_stage`), **fora deste ticket** (mudança de contrato na orquestração). Registrar como débito.

**Risco**: médio para baixo — extrações de baixo comportamento (mover função), sem ciclo de import intrínseco novo (`commands`/`fields`/`status_view` não dependem de `flow`; `flow` importa os três). Benefício: reduzir `flow.py` para ~250 linhas, separação clara, e remover a repetição imperial do formulário.

**Confiança: alta**.

---

## 2. `provider.py` — MÉDIA

**Fato central**: arquivo de 436 linhas, porém coeso — é um *adapter* de infraestrutura (Questionary + Rich) atrás do Protocol. O protocolo `InteractionProvider` (73–211) e o adaptador são coesos; manter apenas. A divisão em módulos separados reduziria a clareza (adapter único). O problema é **complexidade intra-função**:

| Método | Linhas | CCM | Fís |
|---|---|---|---|
| `ask_multi_choice` | 297–367 | **14** | 71 |
| `ask_choice` | 259–295 | **8** | 37 |

**Evidências**:
- `ask_multi_choice` concentra 3 responsabilidades no mesmo corpo: validação do contrato das opções (tamanho = 4, rótulo/ valor não vazios, `checked` bool, `disabled_reason`, valores únicos — 303–342), conversão para `questionary.Choice`, e defesa do container de resposta (None→`InteractionCancelled`, tipo inválido, valores desconhecidos — 344–366).
- **Padrão repetido 4×** (em `ask_text` 249–257, `ask_choice` 284–294, `ask_multi_choice` 349–366, `confirm` 381–389): "se `answer is None` levanta `InteractionCancelled`; depois valida tipo; e inválida com `TypeError`/`ValueError`". É código duplicado (sinal #7).
- **Responsabilidade de saída**: deixa `show_summary` (417–436) no provider atrai 3 imports de `orchestration.summary` (exit_code_for_run/render_summary). Isso mistura "promoção de entrada" com "renderização de resumo" no mesmo objeto.

**Motivo de mudança**: alterar o esquema de validação de opções; alterar render de resumo; trocar o framework. São três forças diferentes em um mesmo arquivo (a terceira reduziria com separação, mas não valeria o custo).

### Plano

- Extrair helpers privados *no mesmo arquivo* (sem novo módulo — evita fragmentação):
  1. `_guard_answer(answer, *, ...)` que centraliza o padrão "None → InteractionCancelled; tipo inválido → TypeError";
2. `_validate_option_tuple(option, index)` com a validação de 303–342 de `ask_multi_choice`;
   3. `_validate_choices` para `ask_choice` (267–293).
- **Decisão adiada**: retirar `show_summary` do `InteractionProvider`, separando `PromptView` (entrada)
  de `SummaryRenderer` (saída). Hoje o `flow` devolve o exit-code via `provider.show_summary` (o modo
  de provider), então a mudança == mudança pública do Protocol. **Não recomendo neste ticket:** é
  mudança de contrato público sem demanda clara — registrar como candidata para o ticket de
  `orchestration` junto da dedup de `summary`. Mas atenção: o provider já delega para o `summary.py`,
  então a responsabilidade já mora no lugar certo.

**Risco**: baixo. Benefício: reduz `ask_multi_choice` (71) e `ask_choice` (37) e elimina duplicação. **Confiança**: alta (evidências quantitativas: CCM 14/8).

---

## 3. `__init__.py` — NÃO RECOMENDADA

13 linhas, um único símbolo público (`run_interactive`, `__all__`), import TTY-gated em `cli/main.py:698–700`. Dividir daria fragmentação — terminaria com um módulo residual de poucas linhas. Confiança alta.

---

## 4. Testes

Arquivos: `test_interactive_flow.py` (201 linhas, 9 testes) + `test_interactive_provider.py` (37 linhas, 1 teste parametrizado × 4). Suíte verde: `pytest tests/test_interactive_*.py --no-cov` → **11 passed** (0.28s). mypy strict: **Success** nos 6 arquivos (2 prod + testes + support). ruff: **31 erros E501** (linhas longas, pré-existentes) + 3 `I001` — sem nada novo.

**Cobertura específica (apenas os 2 arquivos de teste)** — relatório de branch coverage dentro da suíte:
- `flow.py`: **71%** (28 stmts descobertos). **Ramos sem teste**: validação de competência (`_validate_competencia` 109–117), validação `_validate_non_empty_text` (120–128), opção `consolidate` desabilitado/both (339), re-seleção com seleção vazia (370–384), ramo de `_force_commands_for` (434–438), `_is_pre_dispatch_failure` (453–454) e **todo o callback `on_failure`/`on_state` (522–552)**.
- `provider.py`: **56%** — os patches cobrem o caso ctrl+c, mas as **validações de contrato** (`ask_choice` valor inválido/tipo, `ask_multi_choice` 313/320/323/326/329/342/358–364), `show_message` (398), `show_progress` (411–415) e `show_summary` (424–436) ficam sem teste.

**Dificuldade de isolamento observada** (sinal #12 do spec):
- `test_run_guided_flow_end_to_end_happy_path` (test_interactive_flow.py:126–201) é o único teste de fluxo completo externo: redefine `cwd` globalmente (`os.chdir`, 128, efeito global no processo de teste), cria a árvore de diretórios de `configs`/`input`/`roms`, grava YAML de config, CSV de dados e invoca `bootstrap_capa_csv` (import de `pyauditor.excel.capa`) → o teste depende de toda a pilha (config, excel, split, measure…) para cobrir um caminho feliz do flow.
- Do lado dos testes: os testes de `collect_answers`/`select_commands` já têm isolamento razoável via `FakeInteractionProvider`. O caso que apresenta problema é `on_failure` (decisão retry/skip/abort) — não há teste direto; para testá-lo seria preciso disparar `execute_run` com falha *e* interpretar o fake — ou seja, deduzir uma solução de armação de widget. **Isto apoia o argumento de extrair a tradução de decisão para uma função pura** (ex.: `decision_from_choice(choice: str) -> FailureDecision` em `interactive`), testável sem TTY e sem filesystem.
- O `FakeInteractionProvider` (tests/support/fake_interaction_provider.py) não aplica as validators passadas a `ask_text`; uma refatoração do flow que deixasse de usar um validador não pegaria falha (os validadores só são exercidos pelo provider real).

**Testes necessários antes da refatoração** (adicionar à suíte atual):
- flow: `_force_commands_for` (3 casos: report só; órgão MinC sem consolidate; `both` com consolidate → força); `_is_pre_dispatch_failure` (prefixo de `run.py:1011`); decisão de `on_event` → retry/skip/abort; `select_commands` com seleção vazia (re-solicita); `select_commands(orgao="both")` com consolidate disponível.
- provider: validações de contrato (lista de opções vazia/duplicada/`checked` não-bool/`disabled_reason` vazio); `show_message` literal (sem interpretar Rich markup, via console de captura); `show_progress` com cancelamento/exceção; `show_summary` com `log_path` (duas chamadas e exit code 0/1).

**Testes “depois”** (pós-extração): mesma semântica pública — os mesmos `import`s permanecem (mover `collect_fields` interno) — só adicionar novos de funções puras.

---

## 5. Validações recomendadas

```bash
# lint/format (estilo já existente; NÃO corrigir sem pedido — nada será alterado)
.venv/bin/ruff check src/pyauditor/interactive tests/test_interactive_flow.py tests/test_interactive_provider.py

# tipagem estrita
.venv/bin/mypy src/pyauditor/interactive tests/test_interactive_flow.py tests/test_interactive_provider.py tests/support/fake_interaction_provider.py

# testes dos dois arquivos de interactive (sem cobertura)
.venv/bin/pytest tests/test_interactive_flow.py tests/test_interactive_provider.py --no-cov

# suite completa (506, rodada no CI) + cobertura de alvo
.venv/bin/pytest --cov=pyauditor --cov-branch
```

Resultado observado neste ambiente: mypy ok; `ruff` 31 erros somente E501+I001 (pré-existentes); `pytest` 11 passado; cobertura da dupla de arquivos 71% flow / 56% provider (volume da suite exige CI).

---

## 6. Ordem segura de execução

1. Adicionar testes que travam o comportamento atual (seção "antes", acima) — green com código atual.
2. Extração `interactive/fields.py` (formulário) — sem alteração de behavioro: correr suite.
3. Extração `interactive/commands.py` (catálogo + `_force_commands_for`).
4. Extração `interactive/status_view.py` (estado → ícone/estilo).
5. (débito seguinte) mover `_is_pre_dispatch_failure` para a camada de orquestração e eliminar a string mágica.
6. (débito seguinte) dedup de catálogo de comandos/estados com `run.py`/`summary.py` quando outros tickets estiverem fechados; decidir sobre extração de `show_summary` do Protocol.

Risco de cada passo ≤ baixo; nenhum passo muda contrato público de `pyauditor.interactive` nem introduz dependência nova.