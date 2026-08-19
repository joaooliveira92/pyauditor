Type: grilling
Status: resolved

## Question

`docs/spreadsheet.md` especifica (e `inspiration-spreadsheet/afericao_06_2026.xlsx` amplia ainda mais) várias abas nunca implementadas: `CADASTROS` (aba 2 — parâmetros hoje hardcoded em Python), `EVIDENCIAS` (aba 9 — nenhum registro central de evidências, embora `INMS_BASE` tenha colunas para referência/SEI/responsável que nada popula), `PAINEL_GERENCIAL` (aba 14 — dashboard/tendência), e as abas só-mockup `HISTORICO`, `CALCULO_PAGAMENTO`, `CHECKLIST_FISCAL`, `RELATORIO_FISCAL`, `FONTES_E_PREMISSAS`, `SERVICOS_POR_ORGAO`.

Quais dessas são realmente necessárias para o relatório final ser um artefato que a fiscalização aceita, versus quais são elaboração do mockup que não reflete uma exigência real do Termo de Referência? Precisa de uma decisão de prioridade, não uma pesquisa — depende do que a fiscal técnico realmente usa/precisa entregar.

## Answer

Decisão de prioridade tomada no mapa `multi-org-pipeline` (grill com o fiscal, 2026-08-19), respondendo pergunta a pergunta:

- `CADASTROS` (aba 2) e `EVIDENCIAS` (aba 9) — necessárias, implementadas (tickets [[09-cadastros-aba-de-dados-de-referencia]] e [[10-evidencias-registro-de-provas]], ambos `closed`).
- `CALCULO_PAGAMENTO` e `SERVICOS_POR_ORGAO` — necessárias, escopadas para dentro do subcomando `consolidate` (2.1, núcleo financeiro) em vez de abas do relatório por-órgão. Confirmado implementado: `CALCULO_SHEET`/`SERVICOS_SHEET` em `src/pyauditor/excel/consolidate.py`.
- `PAINEL_GERENCIAL`, `HISTORICO`, `CHECKLIST_FISCAL`, `RELATORIO_FISCAL`, `FONTES_E_PREMISSAS` — elaboração do mockup sem exigência confirmada no Termo de Referência; **out of scope** por decisão explícita.

Nenhuma aba pendente restante da lista original — todas ou implementadas ou explicitamente fora de escopo.
