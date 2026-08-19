Type: grilling
Status: resolved

## Question

Decidir o **contrato CLI/dados/output por órgão** — a costura exata que expõe `--orgao` e `consolidate`:

- Input: derivar `data/<órgão>/<AAAA>/<MM>` a partir de `--orgao` + competência. Com `--orgao both`, `measure`/`report` itera os órgãos (1.3 = 1.1 + 1.2, secuencial, sem cruce). Confirmar o contrato de path e a semántica de `both`.
- Outputs: `roms/<órgão>/<comp>/`, `reports/relatorio_<comp>_<orgao>.xlsx`. A consolidada se chama `reports/relatorio_<comp>_consolidado.xlsx`.
- `consolidate <comp>`: contrato de entrada (qué workbooks por órgão exige), o que faz se falta un órgão (erro claro), e como maneja os por-ativo (1.4/1.5/1.14) — uma linha por órgão, sem consolidar.
- `--orgao both` + `consolidate`: se o usuário roda 1.3 e logo 2.1, o 2.1 lê os workbooks que 1.3 deixou — nunca volta a rodar 1.3. Fixar como o garante (só leitura + erro se falta).
- **Re-rodada sobre planilha já decorada (novo, vindo do ticket 02)**: o `consolidate` regenera linhas/valores sugeridos mas **preserva** as células de decisão já preenchidas pelo fiscal (Justificativa/Decisão/Anistia). Definir o contrato de merge: o que é reconstruído, o que é preservado, e como detectar conflito entre decisão do usuário e novo cálculo.

## Answer

Parte decidida e **implementada** (subcomando `--orgao`, 19/08/2026), após a movimentação dos configs para `configs/<órgão>/`:

- `--orgao {MinC,MTur,both}` em `measure`/`report`/`bootstrap`, default `MinC`. `both` itera os dois órgãos sequencialmente, sem cruzar (1.3 = 1.1 + 1.2).
- Config dir derivado: `configs/<órgão>/`; `discover_configs(config_dir, expected_orgao=...)` valida `scope.orgao` (mismatch = erro claro).
- Input: `data_dir/<órgão>/<AAAA>/<MM>`; ROMs: `roms/<órgão>/<comp>/`; relatório: `reports/relatorio_<comp>_<orgao>.xlsx`; capa: `capa_<orgao>.xlsx` (bootstrap por órgão).
- Manifest por órgão derivado: `configs/<órgão>/datasets.yaml`.

Ainda **em aberto** (a decidir):
- O subcomando `consolidate` (2.1) — é o destino do mapa, não implementado aqui.
- Contrato de merge na re-rodada da 2.1 sobre planilha já decorada (preservar células de decisão) — parte do ticket 02, contrastar com el contrato de output al implementar.

## Resolución (19/08/2026)

Ronda 1 de grilling — cerrar os dous puntos abertos do subcomando `consolidate` (2.1), decisions Q1–Q4:

- **Q1 — Input completo obrigatório**: `consolidate` exige o **par completo MinC+MTur** (`reports/relatorio_<comp>_MinC.xlsx` + `reports/relatorio_<comp>_MTur.xlsx`). A consolidada é o punto de fusión dos dous; se falta un órgao → erro claro por órgao, nomeando o workbook ausente (para que o usuario roda 1.4/1.5 dese órgao antes). **Nunca volta a rodar 1.3.**
- **Q2 — CLI agnóstica (sen `--orgao`)**: `consolidate` non leva `--orgao` — é o paso de fusión por definición. Toma só `competencia` (e overrides de `--capa-path`, `--report-dir`). Saída: `reports/relatorio_<comp>_consolidado.xlsx`.
- **Q3 — Merge por chave de fila (re-rodada sobre planilla xa decorada)**: cada ocorrencia identificada por `(indicador, órgao, competencia)`; **recalcula** os campos de cálculo/valor suxerido e **preserva** as columnas de decisión xa preenchidas (`Justificativa`, `Decisión Fiscal`, `Observación`). Conflitos:
  - fila que a nova corrida xa non produce → **aviso** "esta fila desapareceu", **nunca** borrar en silencio unha decisión rexistrada;
  - decisión fiscal que contradí o recalculado (ex.: anistía mantida con `%Ajuste` agora >0) → **aviso de conflito**, sen mutar nin a decisión nin o valor.
- **Q4 — Por-ativo (1.4/1.5/1.14)**: quedan na planilla consolidada, **unha fila por órgao**, sen fusionar, sen achegar glosa. "Non consolidar" = non-fusión, non-ausencia.