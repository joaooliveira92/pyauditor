Type: task
Status: open

## Question

Conjunto de lacunas operacionais/ergonômicas, sem dependência de pesquisa externa — decisão é só de prioridade:

- **Pré-validação ausente**: nada checa a capa por campos obrigatórios não preenchidos (`PREENCHER`/em branco) antes de `report` rodar; o mockup tem um bloco "AVISOS DA GERACAO" que faz isso. Hoje os erros aparecem tarde e um de cada vez.
- **Sem CI**: não há `.github/workflows`, nem linter (`ruff`/`flake8`) configurado — só `mypy --strict` e `pytest` localmente.
- **"Situação geral da aferição" nunca é sugerida automaticamente** — é sempre preenchimento manual do fiscal, mesmo quando o resultado computado (ex.: `GLOSAS` > 0) já indicaria "Conforme com glosa".
- **Sem geração de relatório narrativo** — o ROM Markdown é uma memória de cálculo, não a manifestação técnica assinada que o contrato provavelmente exige como entregável (`RELATORIO_FISCAL` no mockup).

Qual (se algum) desses vale a pena implementar agora, versus aceitar como processo manual do fiscal técnico permanentemente?

## Answer

(aberto)
