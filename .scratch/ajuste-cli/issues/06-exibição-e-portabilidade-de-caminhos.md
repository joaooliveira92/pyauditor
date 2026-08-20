# 06 - Exibição e portabilidade de caminhos

Type: grilling
Status: resolved
Blocked by: 04, 05

## Question

Como tratar **caminhos e formatos numéricos** na saída — para humanos (pt-BR) vs. máquinas (ponto decimal) — e a portabilidade de caminhos Windows/POSIX?

Hoje: caminhos impressos em formato Windows (`roms\MinC\2026-06\INMS-01.md`), o resumo trunca `relatorio_2026-06_consolidado.xl…` via rich, e `total de pontos: 46909.85` usa ponto decimal — misturando apresentação humana e técnica.

Decisões em aberto:
- Módulos `pathlib` para construir/exibir caminhos, preservando o nativo do SO (win32 vs posix).
- Apresentação humana (`46.909,85`) vs. logs técnicos (`46909.85`) — onde cada um se aplica (resumo vs. logs/JSON).
- Exibir caminho completo após a tabela; modo `--no-truncate`; saída `--output json` para automação.
- Necessidade real de Linux/CI/containers hoje, ou somente Windows (provisório)?

Depende de ticket 04 (onde os caminhos/números aparecem) e 05 (formato JSON/logs técnicos).

Contexto: review.md §7 e §8 (baixa prioridade).

## Answer

Fechado por grilling (Q1-Q7, todas aprovadas):

1. **Portabilidade (Q1/Q3)**: provisório "não quebrar" — o código já usa `pathlib.Path` em todo lugar (verificado: nenhum separador `\` gravado fixo no código). Foco: não gravar separadores fixos; caminhos completos no bloco "Artefatos" (nativo guardado via `Path`), relativos no log/JSON (05). **Truncamento banido** (04 já não trunca) — o `--no-truncate` da revisão §7 fica desnecessário.
2. **Formato numérico por superfície (Q2/Q5/Q6)**: humano = pt-BR (`46.909,85`, milhar ponto + decimal vírgula) só no painel "Resultado"; logs técnicos e JSON = ponto decimal (`46909.85`). Auxiliar `fmt_pt_br` em `orchestration/summary.py`. Log `consolidate_generated` corrigido: `glosa` passou de `,.2f` (vírgula) para `.2f` (ponto, máquina).
3. **Linha "Total de pontos" do painel (Q7)**: quando `consolidate` roda, o painel mostra `Total de pontos (consolidado): 46.909,85` — `ConsolidateResult` ganhou `total_pontos` (antes, só `ConsolidationResult` tinha). Duração do painel formatada `1,24 s` (vírgula).
4. **Caminhos com acentos/espaços (Q4)**: já funciona via `str(Path)`; o mojibake do console Windows (cp1252) é do rich, documentado no 04 — fora do escopo.

**Aplicado no código**:
- `cli/consolidate.py`: campo `total_pontos` (float) repassado; log `consolidate_generated` com `glosa` ponto decimal (máquina).
- `orchestration/summary.py`: `fmt_pt_br()` humano; `_consolidado_info` expõe `total_pontos`; `_painel_resultado` com linha "Total de pontos (consolidado)" e duração/glosa em pt-BR.

Testes: `tests/test_orchestration_summary.py::test_fmt_pt_br_formato_humano`. Suíte 263 aprovados; mypy limpo; ruff sem novas violações.

Interfaces: 05 (logs técnicos ponto decimal) e 04 (painel humano). Este ticket **não decide** a névoa "Validação de indicadores" (esperado 14) — segue em aberto.