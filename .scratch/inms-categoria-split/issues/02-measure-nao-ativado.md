# 02 — `measure`: dataset ausente vira "não ativado" (WARNING), não erro

**What to build:** regra geral do engine (`docs/spec/inms-pipeline.md` §14.1, ticket 01 item 15 do
mapa de decisões): quando o CSV de entrada de um indicador não existe para a competência, `measure`
não trata isso como falha de quality gate nem como erro — trata como "esse elemento contratual não
foi demandado/ativado no período". Vale para qualquer um dos 14 indicadores (não é específico de
categoria), incluindo os que passarão a ter configs derivadas pelo `split` (ticket 03) e os INMS sem
categoria (1.8, 1.10). Independente do resto da feature de categoria — pode ser implementado e
mergeado sem esperar por `categorias.yaml`/`split`.

Hoje o `measure` não tem esse comportamento — um CSV ausente provavelmente propaga como falha dura.

**Texto exato do log** (ticket 08 do mapa de decisões, nível `WARNING`, não `ERROR`):

```
WARNING: INMS 1.8 (MinC/2026-06): não ativado — dataset ausente (serviço não requisitado no período)
```

Formato: INMS + órgão + competência entre parênteses (mesmo padrão dos demais logs de `measure`),
motivo curto ao final.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Quando o CSV de um indicador configurado não existe no diretório de dados da competência,
      `measure` emite o `WARNING` acima (com o `contractual_id`/órgão/competência reais) em vez de
      propagar um erro
- [ ] O indicador "não ativado" não gera ROM/JSON de falha — é pulado, mas o resultado geral de
      `measure` (`MeasureResult`/summary) precisa registrar esse estado de forma que `report` e o
      xlsx sintético (ticket 05 deste tracker) consigam distinguir "não ativado" de "medido com
      população zero" (população zero = CSV existe mas não tem linhas que batam num filtro — isso já
      é tratado por outro caminho e não muda)
- [ ] Teste cobrindo: indicador com `source.csv` apontando pra um arquivo inexistente → `measure`
      completa com sucesso, emite o `WARNING`, e o indicador aparece marcado como não ativado no
      resultado/summary
- [ ] `uv run mypy --strict src` e `uv run pytest` verdes
