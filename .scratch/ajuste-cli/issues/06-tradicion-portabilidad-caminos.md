# 06 - Exibição e portabilidade de caminhos

Type: grilling
Status: open
Blocked by: 04, 05

## Question

Como tratar **caminhos e formatos numéricos** na saída — para humanos (pt-BR) vs. máquinas (punto decimal) — e a portabilidade de caminhos Windows/POSIX?

Hoje: caminhos impressos em formato Windows (`roms\MinC\2026-06\INMS-01.md`), o resumo trunca `relatorio_2026-06_consolidado.xl…` via rich, e `total de pontos: 46909.85` usa punto decimal — misturando apresentação humana e técnico.

Decisões em aberto:
- `pathlib` para construir/exibir caminhos, preservando o nativo do SO (win32 vs posix).
- Presentación humana (46.909,85) vs. logs técnicos (46909.85) — onde cada um se aplica (resumo vs. logs/JSON).
- Exibir caminho completo após a tabela; modo `--no-truncate`; saída `--output json` para automação.
- Necesidade real de Linux/CI/containers hoje, ou solo Windows (provisório)?

Depende de ticket 04 (onde os caminhos/números aparecem) e 05 (formato JSON/logs técnicos).

Contexto: review.md §7 e §8 (baixa prioridade).