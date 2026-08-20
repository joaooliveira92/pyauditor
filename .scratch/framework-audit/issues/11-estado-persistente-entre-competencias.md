Type: task
Status: resolved

## Question

Pesquisa dos tickets [[02-rollover-glosa-nao-consumido]] e [[03-reincidencia-nao-rastreada]] confirmou, com citação primária do item 35 do Termo de Referência (`07_modelo_de_gestao.html`, ver `.scratch/inms-pipeline-spec/research/12-glosa-item-35.md`), dois requisitos reais que o pipeline stateless de hoje não atende:

1. **Rollover de glosa**: o excedente acima do teto de 30% mensal deve compor a glosa do mês seguinte (exceto no último mês de vigência do contrato). `compute_glosa` já calcula `saldo_rolado_pct`, mas nada persiste/lê esse valor entre execuções de `report`.
2. **Reincidência (flag de compliance, não multiplicador monetário)**: contar quantas vezes o teto de 30% foi estourado numa janela de 6 meses; ao atingir 3, sinalizar "inexecução parcial do contrato" (aciona sanção administrativa fora do cálculo de glosa).

Ambos exigem a mesma coisa: um histórico persistido entre execuções mensais de `report` (hoje cada run é independente, sem estado). [[04-teto-anual-glosa]] concluiu que **não** há um terceiro requisito de teto anual — só estes dois.

Decisão de prioridade/design necessária: vale implementar esse estado persistente agora (formato: arquivo por competência? aba `HISTORICO` no workbook, cortada como out-of-scope em `.scratch/multi-org-pipeline/map.md`, precisaria ser revisitada? banco local?), ou aceitar como processo manual do fiscal (ele mesmo consulta os workbooks anteriores e ajusta a `%Ajuste`/pontos manualmente) até haver mais pressão real para automatizar?

## Answer

Aprovado (2026-08-19). Desenho:

1. **Histórico por órgão**: `roms/<orgao>/glosa_historico.json`, dict indexado por competência (`{total_points, raw_pct, percentual_ajuste, teto_atingido, saldo_rolado_pct}`), atualizado — não anexado — a cada `report` (idempotente em re-runs). Fica fora das subpastas por competência; não funde MinC/MTur (mesmo padrão de hoje, fusão só em `consolidate`). Sem aba `HISTORICO` nova (já cortada como out-of-scope em `.scratch/multi-org-pipeline/map.md`) e sem banco — ledger JSON simples.
2. **Rollover**: `compute_glosa` ganha `saldo_anterior_pct: float = 0.0`; `report` lê a competência anterior do histórico e soma ao `raw_pct` antes do teto de 30%.
3. **`is_final_month` deixa de ser manual**: derivado comparando a competência atual com o fim de vigência lido da capa (`Vigência` em `capa.py`), em vez do parâmetro hoje sempre `False`.
4. **Reincidência**: após calcular `teto_atingido` do mês, conta quantos dos últimos 6 registros do histórico (incluindo o atual) têm `teto_atingido=true`; 3+ marca `reincidencia_sancao=true`. Superfície: nova coluna "Reincidência (3x/6m)" na aba `GLOSAS` — flag de compliance, sem efeito monetário (conforme [[03-reincidencia-nao-rastreada]]).

Teto anual (04) não entra — pesquisa concluiu que não existe de verdade.

**Implementado (2026-08-19)**:
- `src/pyauditor/excel/glosas.py`: `compute_glosa` ganhou `saldo_anterior_pct`; novo campo `raw_pct` no `GlosaResult`; helpers puros `competencia_anterior`, `janela_reincidencia`, `saldo_anterior_pct_de`, `houve_reincidencia`, `historico_entry`, `read_historico`/`write_historico`.
- `src/pyauditor/excel/report.py`: `compute_report_glosa` (compartilhado entre a aba GLOSAS e a persistência do histórico); aba `GLOSAS` ganhou 2 colunas novas: "Saldo recebido do mês anterior (p.p.)" e "Reincidência (3x/6m)?".
- `src/pyauditor/cli/report.py`: lê/escreve `roms/<orgao>/glosa_historico.json` a cada `report`; ledger indexado por competência (idempotente em re-run).
- **Desvio do desenho aprovado**: `is_final_month` não é derivado automaticamente da "Vigência" da capa — esse campo é texto livre sem formato definido em nenhum lugar do código (capas reais conferidas: campo vazio), então parsing automático seria especulativo e frágil. Em vez disso, virou uma flag explícita `--final-month` no `pyauditor report`, que o fiscal liga manualmente no último mês de vigência do contrato.
- Testes: `tests/test_glosas.py` (helpers puros) + `tests/test_cli_report.py` (`test_run_report_persists_glosa_historico`, `test_run_report_next_competencia_consumes_rollover`, `test_run_report_final_month_does_not_roll_over`). Suite completa: 131 passed, mypy --strict limpo (erro pré-existente em `manifest.py` não relacionado).
