# Glossário

Termos do domínio do projeto, na grafia usada pelo código e pelos documentos.

- **Anexo D** — tabela 28 do Termo de Referência: "Prazos e Níveis Mínimos de Serviço", fonte dos 14 indicadores INMS e das fórmulas de penalidade.
- **Anexo E** — catálogo de itens de desconformidade técnica (106 itens, 22 categorias), usado pelo INMS 1.8.
- **Competência** — mês/ano de apuração, no formato `YYYY-MM` (ex.: `2026-06`).
- **CNI** — Controle Não Implantado, `CNI = QRC − QCSI` (shape `count_difference`, INMS 1.10).
- **INMS** — Indicador de Nível Mínimo de Serviço (contrato 40/2022).
- **Fog** — questionamento deliberadamente em aberto na spec (ex.: schema de entrada do 1.8/1.10).
- **Glosa** — o ajuste monetário do pagamento mensal: `min(30%, Σ Pontos_NMS × 0,001%)` aplicado ao valor-base.
- **hard_failure** — medição em que todas as linhas existentes foram rejeitadas; sinaliza dado ruim, não competência vazia.
- **Manifesto (datasets.yaml)** — mapeia alias (`incidentes`) → arquivo CSV + `delimiter` + `encoding`.
- **Memória de cálculo** — seção do ROM que mostra o passo a passo da conta do indicador (varia por shape).
- **Pontos_NMS** — penalidade em pontos de um indicador; somados no mês para a glosa.
- **QCSI** — Quantidade de Controles de Segurança Implantados.
- **QRC** — Quantidade de Controles Recomendados.
- **Quality gates** — regras de qualidade de dados declaradas no YAML (hoje `not_null`, `in_set`) que rejeitam linhas com motivo.
- **ROM** — "Relatório" (memória de cálculo) Markdown por indicador, gerado por `measure`.
- **Shape** — um dos 5 formatos de cálculo: `ratio`, `segmented_ratio`, `precomputed_table`, `count_difference`, `external_catalog_sum`.
- **Strategy** — implementação de um shape registrada no `SHAPE_REGISTRY`.
- **Sumário (JSON)** — arquivo `<id>.json` ao lado do ROM com a medição flat; o `report` lê somente ele.
- **Valor-base** — "Valor mensal vigente" da capa, usado na glosa monetária.