# 05 — xlsx sintético: geração base

**What to build:** o relatório `sintetico.xlsx` de `docs/spec/inms-pipeline.md` §14.4, gerado por
`split` (proposto no ticket 04 do mapa de decisões, não recontestado) em
`roms/<orgao>/<ano>/<mes>/sintetico.xlsx` — um por órgão/competência, uma aba por INMS com entrada em
`categorias.yaml` (exclui 1.8/1.10, que não têm categoria).

Layout de referência: protótipo aprovado na branch `prototype/inms-xlsx-sintetico-04`
(commit `582d23e`, script `gerar_sintetico.py`) — usar como ponto de partida, não reimplementar do
zero.

Colunas para INMS em `mode: grupo_executor` (uma linha por par categoria × valor de
`Grupo_executor`): `Categoria` | `Nível` | `Grupo executor` | `Linhas` | `Dentro do prazo` | `Fora do
prazo` | `% bruto` | `Tempo médio criação→resolução` (de `DataHoraFim − DataHoraSolicitacao`, sobre
linhas aprovadas pelo quality gate). Contagens são brutas/pré-quality-gate — conferência rápida, não
substitui o ROM oficial. `Nível`: `ATENDIMENTO_N1`→N1, `ATENDIMENTO_N2`→N2, `OPERACAO_N3`→N3,
`MONITORAMENTO_NOC_SOC`→N3; `outros` sem Nível. Abaixo da tabela, subtotais por Nível (soma de
`Linhas`/`Dentro do prazo`/`Fora do prazo`, `% bruto` e tempo médio agregados).

`mode: whole_indicator`: linha única, `Grupo executor` = `"(indicador inteiro)"`, sem bloco de
subtotais.

"Não ativado" (depende do ticket 02 deste tracker para o `measure` expor esse estado): linha única
mesclada com a frase `"Esse serviço não foi requisitado no período selecionado."` no lugar da tabela.

Fora de escopo deste ticket: a aba do INMS 1.14 (multi-ativo × categoria) — ver ticket 06.

**Blocked by:** 03, 02

**Status:** ready-for-agent

- [ ] `split` gera `roms/<orgao>/<ano>/<mes>/sintetico.xlsx` com uma aba por INMS presente em
      `categorias.yaml` (exceto 1.14 — ticket 06)
- [ ] Abas `grupo_executor`: colunas exatas acima, uma linha por (categoria, valor de
      `Grupo_executor`), bloco de subtotais por Nível abaixo da tabela
- [ ] Abas `whole_indicator`: linha única `"(indicador inteiro)"`, sem subtotais
- [ ] INMS "não ativado": linha mesclada com a frase exata acima, sem lançar erro
- [ ] `Tempo médio criação→resolução` calculado corretamente a partir de `DataHoraSolicitacao`/
      `DataHoraFim`
- [ ] Teste de integração gerando o xlsx a partir de fixtures e verificando estrutura de abas/colunas
      (célula a célula onde fizer sentido, não snapshot binário do arquivo)
- [ ] `uv run mypy --strict src` e `uv run pytest` verdes
