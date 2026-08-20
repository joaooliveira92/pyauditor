Type: task
Status: resolved

## Question

Conjunto de lacunas operacionais/ergonômicas, sem dependência de pesquisa externa — decisão é só de prioridade:

- **Pré-validação ausente**: nada checa a capa por campos obrigatórios não preenchidos (`PREENCHER`/em branco) antes de `report` rodar; o mockup tem um bloco "AVISOS DA GERACAO" que faz isso. Hoje os erros aparecem tarde e um de cada vez.
- **Sem CI**: não há `.github/workflows`, nem linter (`ruff`/`flake8`) configurado — só `mypy --strict` e `pytest` localmente.
- **"Situação geral da aferição" nunca é sugerida automaticamente** — é sempre preenchimento manual do fiscal, mesmo quando o resultado computado (ex.: `GLOSAS` > 0) já indicaria "Conforme com glosa".
- **Sem geração de relatório narrativo** — o ROM Markdown é uma memória de cálculo, não a manifestação técnica assinada que o contrato provavelmente exige como entregável (`RELATORIO_FISCAL` no mockup).

Qual (se algum) desses vale a pena implementar agora, versus aceitar como processo manual do fiscal técnico permanentemente?

## Answer

(aberto — nenhum dos quatro itens resolvido; nota de estado)

- **CI**: `.github/workflows/docs.yml` existe (publicação do portal Zensical, commit `36c2da3`), mas não é CI de teste/lint — segue sem `ruff`/`flake8` e sem `pytest`/`mypy --strict` rodando em PR.
- Pré-validação da capa, sugestão automática de "situação geral" e relatório narrativo assinável — sem mudança, nenhum código encontrado.

Segue aberto: decisão de prioridade ainda não tomada para nenhum dos quatro itens.

**Decisão (2026-08-19)**: aceito como processo manual, permanentemente — nenhum dos quatro itens será implementado nesta rodada. Pré-validação da capa, CI real de teste/lint, sugestão automática de "situação geral" e relatório narrativo assinável seguem sendo trabalho manual do fiscal técnico. Reabrir só se houver pressão real (ex.: erro recorrente que a pré-validação evitaria, ou mais de uma pessoa tocando o repo justificando CI).
