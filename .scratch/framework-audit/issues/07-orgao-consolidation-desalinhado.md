Type: grilling
Status: resolved

## Question

`src/pyauditor/excel/orgao_consolidation.py` já implementa e testa o pooling MinC+MTur (`with_orgao_consolidation`) dentro de uma única execução de `report` — ele ativa quando `summaries` contém linhas dos dois órgãos para o mesmo indicador. Mas o fluxo real que o usuário descreveu é dois clones de repositório separados (um por órgão), cada um rodando `measure`/`report` de forma independente, unidos manualmente só depois que ambos tiverem relatório final (ver [[project-multi-org-architecture]] na memória) — um fluxo em que `summaries` nunca vai conter os dois órgãos ao mesmo tempo, então esse código nunca dispara.

Duas leituras possíveis: (1) esse código é resquício de uma suposição de arquitetura anterior e deveria ser removido; ou (2) existe uma etapa 4 planejada (união dos dois `relatorio_*.xlsx`) que ainda não foi construída, e esse código deveria ser adaptado para rodar *nessa* etapa em vez de dentro de `report`. Precisa da decisão do usuário — não é uma pergunta que dá para responder só lendo o código.

## Answer

Leitura (2): existe uma etapa 4, e foi construída — o subcomando `pyauditor consolidate <competencia>` (ver `.scratch/multi-org-pipeline/`). `with_orgao_consolidation` saiu de dentro de `report` e virou a base de `src/pyauditor/excel/consolidate.py` (import em `consolidate.py:39`, chamada em `consolidate.py:288`), que lê os dois `relatorio_<comp>_<orgao>.xlsx` já gerados e nunca refaz `measure`/`report`. `cli/report.py` não referencia mais `orgao_consolidation`. Código não é resquício — foi realocado para o lugar certo do pipeline.
