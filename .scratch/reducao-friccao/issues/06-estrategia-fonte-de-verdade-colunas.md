# 06 — Estratégia como fonte de verdade das colunas referenciadas

**What to build:** a validação de que todo campo de coluna referenciado na config de um indicador existe no header do CSV deixa de carregar uma lista fixa de atributos que "conhece todos os shapes". Cada estratégia passa a declarar os próprios atributos de coluna do seu `calculation`, e a validação pergunta à estratégia. Adicionar um atributo novo (ou um shape novo) para de exigir mexer na validação — menos um dos sete pontos de toque no registro de um shape.

**Blocked by:** 02 — rede de testes dos helpers de estratégia (centraliza o contrato comum de cálculo antes de cada shape declarar coisas novas).

**Status:** ready-for-agent

- [ ] Para os cinco shapes atuais, o conjunto de colunas validado é idêntico ao de hoje (regressão coberta por teste: coluna ausente continua derrubando com a mesma mensagem; competência vazia continua rebaixada a WARN).
- [ ] Cada estratégia declara seus atributos de coluna (sem duplicação com a validação); a lista fixa conhecida da validação some.
- [ ] Adicionar um atributo de coluna novo a um `calculation` não exige editar a validação.
- [ ] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes; cobertura não cai.

## Contexto (do relatório de fricção)

A validação de colunas mantém uma lista hardcoded de nomes de atributo supostos por shape; registrar um shape tocava aí um de sete pontos, sem nenhum deles óbvio a partir do contrato da estratégia.