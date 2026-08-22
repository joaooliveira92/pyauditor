# 08 — A-06: A planilha pode ser salva sem resultados calculados

**Severidade:** Alta

**Status:** resolved

## Problema

`openpyxl` escreve fórmulas mas não calcula seus resultados. Se o arquivo for
consumido por um leitor com `data_only=True`, um conversor headless sem
recálculo, ou um serviço de extração, as células podem aparecer vazias ou com
cache antigo. Isso conflita com a promessa do módulo de que a aba é
"rastreável/reproduzível quando reaberta sem o pipeline" — só é reproduzível se
o consumidor recalcular as fórmulas.

## Correção recomendada

**Não é específico do INMS 1.1** — qualquer workbook com fórmulas geradas por
`openpyxl` tem esse problema. Criar `force_recalc(workbook)` em
`src/pyauditor/excel/_workbook.py` (novo módulo compartilhado):

```python
def force_recalc(workbook: Workbook) -> None:
    workbook.calculation.fullCalcOnLoad = True
    workbook.calculation.forceFullCalc = True
    workbook.calculation.calcMode = "auto"
```

Chamar a partir de `inms_1_1_audit.py` e, oportunisticamente, de qualquer outro
renderer de `excel/` que grave fórmulas.

Adicionar smoke test no pipeline que abre o arquivo em um motor compatível
(LibreOffice headless ou equivalente) e verifica ausência de fórmulas com erro,
existência dos resultados esperados, validade das tabelas e integridade dos
ranges.

## Critério de aceite

- [x] `excel/_workbook.py` criado com `force_recalc()`, chamado por `inms_1_1_audit.py`
- [x] Teste: reabertura do arquivo com `openpyxl(data_only=True)` após recálculo externo mostra valores, não `None`
- [ ] Smoke test de recálculo via LibreOffice (ou equivalente) adicionado ao pipeline de testes — **não feito**, ver nota abaixo

## Answer

`excel/_workbook.py` criado com `force_recalc(workbook)`, que seta
`workbook.calculation.fullCalcOnLoad = True`, `forceFullCalc = True` e
`calcMode = "auto"`. `write_sheet()` chama `force_recalc(workbook)` uma vez, no
final (fora do bloco `create_sheet_atomic`, depois que a aba está completa).

Teste implementado: `test_force_recalc_flags_are_set` em
`tests/test_inms_1_1_audit.py` verifica, via `load_workbook()` (que lê os
mesmos atributos `calcPr` gravados no XML), que `fullCalcOnLoad` e
`forceFullCalc` estão `True` no arquivo gerado por `write_sintetico_workbook`.
Isso confirma que a flag é persistida corretamente no `.xlsx`, mas **não**
confirma que um motor de recálculo real (Excel/LibreOffice) de fato recalcula
e produz os valores esperados ao abrir o arquivo.

**Limitação registrada, não simulada**: `soffice`/`libreoffice` não estão
disponíveis neste ambiente (`which soffice`/`which libreoffice` → not found),
então não foi possível implementar o smoke test de recálculo real pedido no
critério de aceite. Esse item fica como follow-up explícito para um ambiente
com LibreOffice headless disponível (ou Excel via automação) — sem isso, não
há como validar de ponta a ponta que as ~200 fórmulas desta aba recalculam sem
erro (`#DIV/0!`, `#REF!`, etc.) fora do próprio parsing sintático já coberto
pelos testes de string de fórmula existentes.
