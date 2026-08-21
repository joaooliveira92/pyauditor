---
Type: grilling
Status: resolved
Blocked by: 01
---

# Semântica fina dos avisos do filtro

## Question

Fechar as mensagens decididas no mapa (Q3): o WARN de zero linhas no período é emitido por indicador×órgão? E categoria splitada com zero linhas (hoje é estado normal, não anomalia)? Texto exato do WARN e do INFO de descarte (contagem por dataset). Interação com quality gates e acceptance_test: rodam sobre o dataset já filtrado? O que registra o sidecar/summary sobre linhas descartadas?

## Answer

Aprovado pelo humano (2026-08-21):

1. **Emissão do WARN de janela vazia**: uma única vez por (órgão, arquivo bruto). Split emite para os brutos que processa; measure emite só para whole_indicator (configs derivadas `_split` não emitem — o bruto já avisou no split); sintetico nunca emite (mesma passada do split). Sem estado global: cada chamador conhece seu papel.
2. **Textos**: um evento de log por dataset com contagens estruturadas. WARN quando havia linhas e nenhuma caiu na janela: `nenhuma linha no período {início}–{fim} — o arquivo corresponde à competência?`. INFO quando misto: `{n} linha(s) fora do período descartada(s)` + `e {k} sem data legível` sob `--strict`. Dataset vazio de fábrica: nenhum aviso novo (estado legítimo preservado, `hard_failure` inalterado).
3. **Ordem do pipeline**: quality gates e acceptance_test rodam sobre o dataset pós-filtro. A seção "Linhas aprovadas pelo quality gate" do ROM ganha a linha "Fora do período descartadas: N".
4. **Sidecar**: `IndicatorSummary` ganha `dropped_out_of_period: int | None = None` e `undated_dropped: int | None = None` (None quando o filtro não rodou — testes unitários sem período); sidecar antigo segue carregando pelos defaults; consolidado ignora os campos por ora (exibição decide na spec).
5. Categoria splitada vazia pós-janela segue estado normal de hoje (sem WARN além do existente).
