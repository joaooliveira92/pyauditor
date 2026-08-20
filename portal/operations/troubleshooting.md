# Problemas conhecidos e recuperação

Coleta de sintomas, causas e resolução. Baseado no comportamento real da CLI e
do engine.

## Diagnóstico geral

Sempre comece pelo log da execução: cada comando grava
`pyauditor-<comando>[-<competência>]-<datahora>.log` no diretório de saída.
O log distingue erro de config (fail antes de ler CSV) de falha de medição
(`hard_failure`, depois dos quality gates).

## Falhas da CLI

### `competência inválida`

- **Sintoma:** `error: competência inválida 'xxx': esperado YYYY-MM`.
- **Causa:** argumento não segue `YYYY-MM`.
- **Recuperação:** use o formato `2026-06`.

### `pyauditor: comando desconhecido`

- **Causa:** subcomando digitado errado.
- **Recuperação:** `pyauditor --help` lista `bootstrap`, `measure`, `report`,
  `consolidate` e `run`.

### `capa não encontrada` (no report)

- **Causa:** `bootstrap` não rodou, `--capa-path` errado, ou o `--orgao` não
  bate com o arquivo `capa_<orgao>.xlsx` esperado.
- **Recuperação:** rode [Crie a capa do contrato](../guides/bootstrap-capa.md)
  e confira o caminho por órgão (`capa_MinC.xlsx` / `capa_MTur.xlsx`).

### `nenhum sumário de medição (.json) encontrado`

- **Causa:** `measure` não rodou para a competência/órgão, ou os `.json`
  foram apagados.
- **Recuperação:** rode [Meça uma competência](../guides/measure-indicators.md);
  `report` só consome os JSONs de `roms/<orgao>/<competencia>/`.

## Falhas de medição (por indicador)

O `measure` não aborta quando um indicador falha — loga e segue. Exit code `1`
ao final.

### `hard_failure` de um indicador

- **Causa:** todas as linhas **existentes** no CSV foram rejeitadas pelos
  quality gates (ex.: `DataHoraFim` nulo com `No prazo = S`).
- **Diferente de:** CSV vazio de origem (competência sem lançamentos, ex.:
  1.3/1.8/1.9/1.10 antes da digitação manual) — isso **não** é falha dura.
- **Recuperação:** abra o ROM gerado (`roms/<orgao>/<competencia>/<id>.md`), seção
  Rejeições, para ver ID + motivo; corrija os dados ou ajuste os gates se
  declarar errado (não mude os gates para "passar" dados ruins sem validar a
  regra de negócio).

### `source.dataset=... requires a manifest, but none was provided`

- **Causa:** config usa `source.dataset`, mas `configs/<orgao>/datasets.yaml` não
  existe / não foi passado via `--manifest`.
- **Recuperação:** forneça o manifesto.

### `dataset alias 'X' not found in manifest`

- **Causa:** alias no config não bate com `datasets.yaml`.
- **Recuperação:** corrija o alias ou adicione a entrada. A mensagem lista os
  aliases disponíveis.

### `aggregation: precomputed espera exatamente 1 linha por CSV`

- **Causa:** shape `ratio` com `aggregation: precomputed`, mas o CSV tem mais
  de uma linha (config de um único ativo deve ter 1 registro por arquivo).
- **Recuperação:** use um CSV de 1 registro por ativo/serviço, ou o shape
  `precomputed_table` para tabela multi-linha.

## Falhas na consolidação

### `GLOSAS` sem valor da glosa

- **Causa:** `Valor mensal vigente` vazio na capa.
- **Recuperação:** preencha o campo na `capa_<orgao>.xlsx` e re-rode `report`
  (log avisa).

### `CADASTROS` omitido

- **Causa:** falha ao carregar configs (`--config-dir`), loga aviso.
- **Recuperação:** corrija o erro do config e re-rode. `INMS_BASE` e grupos
  continuam sendo gerados.

### `consolidate` sem os relatórios dos dois órgãos

- **Causa:** `relatorio_<comp>_MinC.xlsx` ou `_MTur.xlsx` não existem — o
  `consolidate` exige os dois (não re-executa `measure`/`report`).
- **Recuperação:** rode `report` para cada órgão antes, ou use
  `run <competencia> --orgao both` (que encadeia as quatro fases).

## Dados sensíveis

- **Nunca versionar `input/`** — CSVs com PII (nome/solicitante/técnico).
  Fixtures de teste devem ser sintéticas/anonimizadas
  ([Organização dos dados](../concepts/data-layout.md)).

## Perguntas em aberto do contratual (não bloqueiam o pipeline)

- Schema de origem/ingestão de INMS 1.8 (ocorrências Anexo E) e INMS 1.10
  (controles de segurança): há schemas provisórios de digitação manual
  documentados e testados (`tests/fixtures/manual_entry_examples/`), mas a
  pergunta de qual sistema real alimenta esses dados continua aberta para a
  fiscalização.
- Fórmula de consolidação MinC/MTur específica para os indicadores por ativo
  (1.4, 1.5, 1.14): não localizada (o `consolidate` não funde esses 3).

Detalhe: [spec §13](https://github.com/joaooliveira92/pyauditor/blob/master/docs/spec/inms-pipeline.md).