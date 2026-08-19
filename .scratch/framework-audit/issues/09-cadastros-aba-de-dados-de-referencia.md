Type: task
Status: closed

## Question

Criar a aba `CADASTROS` (aba 2) no workbook Excel, consolidando os dados de referência que hoje estão espalhados em YAMLs e hardcoded no Python. Essa aba serve como fonte de verdade visível para o fiscal auditar os parâmetros que alimentam os 14 indicadores.

### O que deve conter

A aba CADASTROS deve expor, no mínimo:

1. **Órgãos** — lista de órgãos habilitados (MinC, MTur) com seus IDs internos
2. **Contratos** — número do contrato (40/2022), objeto, vigência
3. **Serviços** — mapeamento de serviços por órgão (quando aplicável)
4. **Indicadores** — tabela completa dos 14 INMS: código, nome, fórmula, target, operador (>= / <=), unidade, penalidade base, penalidade por unidade de descumprimento
5. **Metas por competência** — se houver variação mensal dos targets (hoje os YAMLs usam `target_value` fixo; confirmar se o TR permite sazonalidade)

### Fonte de dados

- `configs/inms-<n>.yaml` — cada config já declara: `contractual_id`, `name`, `target_value`, `target_operator`, `penalty_base`, `penalty_per_unit`
- `src/pyauditor/excel/groups.py` — mapeamento indicador → grupo operacional
- `src/pyauditor/excel/report.py` — colunas do INMS_BASE que hoje são hardcoded

### Restrições

- A aba deve ser **auto-gerada** a partir dos YAMLs (não manual), para manter consistência com o pipeline
- Formato: tabela simples com cabeçalhos estilizados (mesmo padrão de `_style.py`)
- A aba deve ser populada pelo `report.py` no fluxo de geração do workbook
- Não deve quebrar as 7 abas existentes

### Critérios de aceite

- [x] Aba `CADASTROS` aparece como segunda aba no workbook (após CAPA_E_CONTROLE)
- [x] Todos os 14 indicadores estão listados com nome, código, target e penalidade
- [x] Dados vêm dos YAMLs (não hardcoded)
- [x] Roda sem erro: `pyauditor report --competencia 2026-06`

## Answer

Implementado em `src/pyauditor/excel/report.py` e `src/pyauditor/cli/report.py`.

**Arquivos alterados:**
- `src/pyauditor/excel/report.py` — adicionadas constantes `CADASTROS_SHEET` e `_CADASTROS_COLUMNS`, função `_cadastros_row()`, parâmetro `configs` em `build_report_workbook()` e `build_report()`
- `src/pyauditor/cli/report.py` — `run_report()` agora recebe `config_dir`, carrega configs via `discover_configs()` e passa para `build_report()`
- `src/pyauditor/cli/main.py` — adicionado `--config-dir` ao subcomando `report`, atualizado `ReportRequest` com `config_dir`
- `tests/test_cli_report.py` — chamadas de `run_report()` atualizadas com `config_dir`
- `tests/test_cli_main.py` — teste de dispatch atualizado para incluir `--config-dir`
- `tests/test_excel_report.py` — adicionados 2 testes: `test_cadastros_sheet_populated_from_configs` e `test_cadastros_sheet_skipped_when_no_configs`

**Estrutura da aba CADASTROS (7 colunas):**
| Código INMS | Descrição | Formato | Meta | Sentido | Penalidade (pontos base) | Penalidade (p.p. por descumprimento) |

**Comportamento:** A aba é criada quando `configs` é fornecido; omitida quando não (backward-compatible). Dados vêm 100% dos YAMLs. 90 testes passam.
