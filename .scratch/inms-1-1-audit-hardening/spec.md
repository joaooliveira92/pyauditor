# Hardening de `inms_1_1_audit.py`

## Contexto

Auditoria completa das ~990 linhas de `src/pyauditor/excel/inms_1_1_audit.py`, cobrindo
sintaxe, fórmulas Excel, integridade dos cálculos, segurança dos dados brutos,
comportamento com entradas vazias/inválidas, compatibilidade com openpyxl e
rastreabilidade da auditoria.

O arquivo compila e tem boa estrutura (separação em seções, type hints, constantes
para posições/formatos, fórmulas auditáveis no próprio Excel), mas confia demais na
qualidade perfeita do CSV de entrada e no comportamento implícito do Excel. Os
problemas mais graves não são cosméticos: podem gerar resultado contratual
incorreto, narrativa executiva contraditória, `#DIV/0!` silencioso e execução de
fórmulas vindas de dados externos (formula injection).

Nota atual de prontidão para produção: 5,5/10 — não recomendado promover sem as
correções críticas e de alta severidade.

## Tickets

Um ticket por achado da auditoria, mantendo o identificador original
(`C-`/`A-`/`M-`/`B-`) no nome do arquivo para rastreabilidade com o relatório
original.

Ordem de correção recomendada:

1. **Bloqueadores de produção** (críticos + altos): 01–09
2. **Segunda etapa** (médios): 10–17
3. **Hardening** (baixos): 18–22

## Reuso: extrair utilitários genéricos para módulos compartilhados

Nem todo achado é específico do INMS 1.1. Vários são utilitários genéricos de
geração de Excel (sanitização, parsing de datas, controle de recálculo,
unicidade de nomes de tabela, criação atômica de aba) que outros renderers
(`capa.py`, `report.py`, `consolidate.py`, `sintetico.py`, futuros indicadores)
também vão precisar. Para esses, a correção não deve ficar como função privada
de `inms_1_1_audit.py` — deve virar módulo compartilhado em `src/pyauditor/excel/`,
seguindo o padrão já usado por `_style.py` (estilos) e `_csv_verbatim.py`
(leitura crua de CSV): prefixo `_`, docstring de módulo explicando quem reusa,
sem dependência do domínio INMS.

Módulos compartilhados propostos:

- `excel/_safety.py` — `safe_excel_text()`, sanitização contra formula
  injection (ticket 01 / C-01). Qualquer renderer que grave texto vindo de
  CSV/YAML externo deve usar essa função, não só o INMS 1.1.
- `excel/_datetime.py` — parsing estruturado de datas (`parse_dt()` retornando
  resultado tipado, não `None` silencioso) e a constante de tolerância de prazo
  (ticket 02 / C-02, ticket 13 / M-04).
- `excel/_workbook.py` — flags de recálculo forçado (`force_recalc(workbook)`),
  criação atômica de aba (`create_sheet_atomic()`), e geração de nome de tabela
  único por workbook (`unique_table_name()`) — tickets 08/A-06, 17/M-08, 15/M-06.

Achados que continuam específicos do domínio INMS 1.1 (não extrair): A-02
(narrativa executiva), A-03 (operador de meta), A-07 (validação de parâmetros de
penalidade), M-01, M-02, M-03, M-07 — esses dependem da estrutura de seções e das
regras de negócio do INMS 1.1 e devem ficar no módulo atual.

A-04 (normalização "S"/"N") é uma decisão de caso a caso: se outros relatórios
ITSM usarem o mesmo vocabulário "No prazo", vale extrair para
`excel/_datetime.py` ou um `excel/_itsm.py`; caso contrário mantém local. Avaliar
ao implementar o ticket 06.

## Lacunas de teste identificadas

Além dos tickets de correção, a auditoria original levantou uma matriz mínima de
casos de teste que hoje não existem (zero incidentes, datas malformadas,
encerramento anterior à abertura, formula injection por campo, operador `<=`,
`penalty_step_size_pct == 0`, duas abas no mesmo workbook, reabertura com
`data_only=True`, etc.). Cada ticket de correção deve incluir o(s) teste(s)
relevante(s) dessa lista como critério de aceite.
