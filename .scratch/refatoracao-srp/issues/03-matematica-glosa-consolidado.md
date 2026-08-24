# 03 — Extrair matemática da glosa/pagamento do consolidado

Type: task

**What to build:** a regra financeira do workbook consolidado passa a ser calculada por funções puras que retornam valores, não células. A glosa por ocorrência, as faixas, a decisão de anistia e o cálculo de pagamento (rateio MinC/MTur, teto, rollover) saem de `excel/consolidate/workbook.py` para um módulo de matemática (`excel/consolidate/_glosa_math.py`); `build_glosas` e `build_calculo` passam a consumir as funções puras e apenas escrever as células no workbook.

**Blocked by:** 01 — rede de testes da matemática financeira.

**Status:** resolved

- [x] Cálculos retornam números/valores; nenhuma escrita de célula dentro do módulo de matemática.
- [x] `build_glosas` e `build_calculo` mantêm assinatura e células resultantes idênticas.
- [x] Semântica de anistia/decisão fiscal e rollover preservada (testes do 01 cobrem).
- [x] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes.

## Contexto (do relatório SRP)

`excel/consolidate/workbook.py` (664 físicas, 20 imports): `build_glosas` 126 linhas, `build_calculo` 84. É a mistura domínio (regra financeira) × infraestrutura (Excel) mais clara do projeto. Consumidores: `cli/consolidate.py`, `test_excel_consolidate.py`, `test_cli_consolidate.py`.

## Answer

A matemática financeira restante de `workbook.py` saiu do builder para módulos puros (sem `openpyxl`):

- **`excel/consolidate/_calculo_calcs.py`** (novo) — aritmética da aba `CALCULO_PAGAMENTO`: `glosa_valor_sobre_bruto` (ex-`_glosa_bruto` de `workbook.py`) e `compute_calculo_row(rateio, base, pontos) -> CalculoRowValues`, que entrega os valores de todas as linhas de uma coluna (rateio, bruto, pontos, glosa, outros, recomendado). `build_calculo` agora só escreve células, aplica formato monetário/percentual e faz o bold/borda — o `if/elif` por `label.startswith` virou um índice sobre `CalculoRowValues` (o que elimina de vez a fragilidade da costura de espaços da label).
- **`excel/consolidate/_glosa_calcs.py`** (ampliado) — `ocorrencia_glosa(pontos, valor_base) -> OcorrenciaGlosa` (o `pct`/`valor_glosa` que `build_glosas` calculava inline) e `faixa_descumprimento(summary)` (ex-`_faixa`). `build_glosas` consome as duas funções puras e só trata I/O de linha/estilo.
- `workbook.py` removeu `_faixa` e `_glosa_bruto`; `compute_glosa` deixou de ser importado. Nenhuma célula nasce nos módulos de matemática. `__init__.py` (fachada) inalterado.

Note de escopo: o ticket pedia um único módulo `_glosa_math.py`; como `_glosa_calcs` já existia (ticket 04 SRP anterior), a novidade da aba de pagamento foi parar em `_calculo_calcs.py` e as adições de glosa por ocorrência/faixa em `_glosa_calcs.py` — dois módulos coesos em vez de um genérico.

Células resultantes idênticas, confirmado pelos testes existentes de assert por valor (`test_excel_consolidate.py`, `test_cli_consolidate.py`) + a rede de testes do ticket 01, atualizada para importar de `_calculo_calcs`/`_glosa_calcs`.

Validação: `uv run pytest` 586 passados, cobertura 89.40% (gate 85% ok); `uv run ty check`, `uv run ruff check`, `uv run ruff format --check` e `uv run bandit` verdes.