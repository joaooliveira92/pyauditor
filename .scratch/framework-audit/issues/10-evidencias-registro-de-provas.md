Type: task
Status: closed

## Question

Criar a aba `EVIDENCIAS` (aba 9) no workbook Excel, servindo como registro central de evidências que sustentam os valores apurados no INMS_BASE. Hoje, o fiscal precisa rastrear referências, SEI e responsável manualmente — essa aba automatiza o vínculo.

### O que deve conter

1. **Competência** — mês de referência
2. **Código INMS** — qual indicador a evidência sustenta
3. **Tipo de evidência** — classificação (ex: "planilha original", "print de sistema", "documento SEI", "e-mail de confirmação")
4. **Descrição** — resumo do que a evidência comprova
5. **Fonte/URL** — link ou referência ao documento (SEI, SharePoint, arquivo local)
6. **Responsável pela coleta** — quem compilou a evidência
7. **Data de coleta** — quando foi obtida
8. **Status** — "Pendente", "Coletada", "Validada"

### Integração com INMS_BASE

A coluna 22-26 do INMS_BASE hoje é toda blank (campos manuais). A aba EVIDENCIAS deve permitir que o fiscal preencha essas colunas referenciando registros desta aba, criando o vínculo: "este resultado do INMS 1.1 tem estas 3 evidências".

### Fonte de dados

Hoje não há fonte automatizada — a aba é **estrutura para preenchimento manual pelo fiscal**. O pipeline deve:
- Criar a aba com a estrutura correta
- Pré-popular as linhas com um registro por indicador + competência (status = "Pendente")
- Não tentar popular descrição/fonte/responsável (dados manuais)

### Restrições

- A aba deve ser criada pelo `report.py` no fluxo de geração
- Formato: tabela com validação de dropdown nas colunas "Tipo de evidência" e "Status"
- Deve suportar múltiplas evidências por indicador (uma evidência por linha)
- Não deve quebrar as abas existentes

### Critérios de aceite

- [x] Aba `EVIDENCIAS` aparece no workbook (após GLOSAS)
- [x] Pré-populada com 14 linhas (uma por INMS) para a competência atual
- [x] Dropdowns funcionam para "Tipo de evidência" e "Status"
- [x] Colunas do INMS_BASE (22-26) ficam linkadas conceitualmente à esta aba
- [x] Roda sem erro: `pyauditor report --competencia 2026-06`

## Answer

Implementado em `src/pyauditor/excel/report.py`.

**Arquivos alterados:**
- `src/pyauditor/excel/report.py` — adicionadas constantes `EVIDENCIAS_SHEET`, `_EVIDENCIAS_COLUMNS`, `_EVIDENCIAS_TIPOS`, `_EVIDENCIAS_STATUS`; função `_evidencias_row()` e `_build_evidencias_sheet()`; integração em `build_report_workbook()`
- `tests/test_excel_report.py` — adicionados 3 testes: `test_evidencias_sheet_populated_from_configs`, `test_evidencias_sheet_has_dropdown_validations`, `test_evidencias_sheet_skipped_when_no_configs`

**Estrutura da aba EVIDENCIAS (8 colunas):**
| Competência | Código INMS | Tipo de evidência | Descrição | Fonte/URL | Responsável pela coleta | Data de coleta | Status |

**Comportamento:**
- Pré-popula 1 linha por config (indicador), com Competência e Status="Pendente"
- Dropdown "Tipo de evidência": Planilha original, Print de sistema, Documento SEI, E-mail de confirmação, Relatório de monitoramento, Foto/registro visual, Outro
- Dropdown "Status": Pendente, Coletada, Validada
- A aba é criada quando `configs` é fornecido; omitida quando não (backward-compatible)
- 93 testes passam.
