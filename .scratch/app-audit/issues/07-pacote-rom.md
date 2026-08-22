# 07 — Análise SRP do pacote rom

Type: research
Status: resolved
Blocked by: —

## Question

Analisar o pacote `src/pyauditor/rom/` (render.py 352, summary.py 137, loading.py 52, dedup.py 40) com lente de SRP: render como montagem de markdown ROM, summary como computação de resumo por indicador×categoria, loading (leitura de dados), dedup (merge). Verificar separação render (apresentação) vs. cálculo (domínio), e a hipótese de um `rom` que tanto lê da fonte quanto renderiza. Classificação e plano por arquivo com impacto em API pública.

## Answer

Candidatos do pacote `rom/`, com prioridade (detalhes em
`.scratch/app-audit/notes/pacote-rom.md`):

- **`render.py` (352 linhas) — MÉDIA**: achado principal do pacote. A hipótese
  de "rom que lê a fonte e renderiza" **não procede** — a leitura de fonte
  (CSV) fica na engine (`pipeline.py:measurement_source`); `render.py` recebe o
  `MeasurementResult` já processado e `loading.py` lê só sidecar JSON (para
  `report`/`consolidate`). O vazamento real de domínio→apresentação é
  `_render_ressalva_interpretativa` (`render.py:161-194`), que **recalcula** as
  leituras linear/degraus da penalidade (`shortfall` + `math.floor/ceil`) em
  vez de formatar — regra contratual no meio do Markdown. Plano: extrair
  `penalty_interpretation()` para a engine, corrigir o `KeyError` cru do
  dispatch (`render.py:267`) e deduplicar o título; API pública preservada.
- **`summary.py` (137) — BAIXA**: DTO `IndicatorSummary` + validação de borda +
  pool delegado a `SHAPE_REGISTRY` (fonte única, correto). Higiene apenas
  (`assert` em produção `summary.py:56`, `import math` local `summary.py:80`).
- **`loading.py` (52) — BAIXA**: 2 funções coesas de leitura de artefatos; cc 6
  em `load_summaries`; dependência a vigiar: importa `excel/objetos.py`.
- **`dedup.py` (40) — NÃO RECOMENDADA**: 16 stmts, coesão única, 100% coberto —
  não dividir.
- **`__init__.py` (vazio) — NÃO RECOMENDADA**: API pública implícita (consumo
  via `pyauditor.rom.<submod>`), sem `__all__`; apenas observar.

Validação: mypy strict limpo; ruff 75×E501 + 2×S101 pré-existentes; 127 testes
das suítes do pacote + consumidores passando (radon/xenon indisponíveis —
complexidade via AST, limitação registrada na nota).