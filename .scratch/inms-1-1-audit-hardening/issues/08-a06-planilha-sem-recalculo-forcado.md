# 08 — A-06: A planilha pode ser salva sem resultados calculados

**Severidade:** Alta

**Status:** needs-triage

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

- [ ] `excel/_workbook.py` criado com `force_recalc()`, chamado por `inms_1_1_audit.py`
- [ ] Teste: reabertura do arquivo com `openpyxl(data_only=True)` após recálculo externo mostra valores, não `None`
- [ ] Smoke test de recálculo via LibreOffice (ou equivalente) adicionado ao pipeline de testes
