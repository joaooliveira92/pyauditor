# 03 — Extrair matemática da glosa/pagamento do consolidado

Type: task

**What to build:** a regra financeira do workbook consolidado passa a ser calculada por funções puras que retornam valores, não células. A glosa por ocorrência, as faixas, a decisão de anistia e o cálculo de pagamento (rateio MinC/MTur, teto, rollover) saem de `excel/consolidate/workbook.py` para um módulo de matemática (`excel/consolidate/_glosa_math.py`); `build_glosas` e `build_calculo` passam a consumir as funções puras e apenas escrever as células no workbook.

**Blocked by:** 01 — rede de testes da matemática financeira.

**Status:** ready-for-agent

- [ ] Cálculos retornam números/valores; nenhuma escrita de célula dentro do módulo de matemática.
- [ ] `build_glosas` e `build_calculo` mantêm assinatura e células resultantes idênticas.
- [ ] Semântica de anistia/decisão fiscal e rollover preservada (testes do 01 cobrem).
- [ ] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes.

## Contexto (do relatório SRP)

`excel/consolidate/workbook.py` (664 físicas, 20 imports): `build_glosas` 126 linhas, `build_calculo` 84. É a mistura domínio (regra financeira) × infraestrutura (Excel) mais clara do projeto. Consumidores: `cli/consolidate.py`, `test_excel_consolidate.py`, `test_cli_consolidate.py`.