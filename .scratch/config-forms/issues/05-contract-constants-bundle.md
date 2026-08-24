# Contract-constants bundle form

- **Status:** resolved
- **Type:** wayfinder:grilling
- **Blocked by:** 01

## Question

Três arquivos globais pequenos, sem órgão, sem aninhamento:
`dados_contratuais.yaml` (10 chaves, todas string escalar),
`ajuste_inms.yaml` e `desconto_regulatório.yaml` (cada um só `formula` +
`descricao`, ambos string). Decisão do charting: uma tela só, não três
formulários separados. Falta decidir: layout dentro dessa tela (uma seção
por arquivo? uma tabela chave/valor unificada?), se `formula` merece
tratamento especial (é uma expressão matemática em texto — syntax highlight
seria over-engineering pra 2 campos, mas confirmar), e o endpoint backend
(`/api/contrato` único cobrindo os 3 arquivos, ou 3 endpoints finos
reusando o padrão genérico de `/api/file` já existente?).

Carrega execução: implementar como parte da resolução.

## Answer

Layout: uma tela, uma `<section>` por arquivo (título + caminho do arquivo
+ campos), reusando o form engine genérico (`renderChildren`) já que os três
arquivos são mapeamentos rasos string→string — nenhum componente bespoke
necessário.

`formula` não ganhou tratamento especial: confirmado que syntax highlight
seria over-engineering pra um único campo de texto por arquivo — renderiza
como `<input>` de uma linha, igual a qualquer outro campo string. `descricao`
é a única exceção adicionada ao form engine genérico: por nome de chave,
renderiza como `<textarea rows="3">` em vez de `<input>` de uma linha, já
que é um parágrafo (não uma expressão curta como `formula`).

Backend: um único endpoint `GET /api/contrato` / `PUT /api/contrato`
(`src/ui/server.py` + `src/ui/contrato_form.py`) cobrindo os 3 arquivos —
não 3 endpoints finos, e não o padrão genérico de `/api/file` (que não
teria como validar a forma "mapeamento string→string" nem devolver os 3
arquivos already-parsed numa única viagem). Nenhum dos 3 arquivos tem
modelo pydantic hoje — `ajuste_inms.yaml`/`desconto_regulatório.yaml` nem
são lidos pelo pipeline (só documentam fórmula/descrição usadas na
composição do `sintetico.xlsx`) — validação própria em
`contrato_form._validate_kv`: mapeamento raso, chaves e valores devem ser
texto, mesma regra que `excel/dados_contratuais.py::read_dados_contratuais_fields`
já assume pro arquivo que *é* lido pelo pipeline. Testado em
`tests/test_ui_contrato_form.py` + `tests/test_ui_server.py`.
