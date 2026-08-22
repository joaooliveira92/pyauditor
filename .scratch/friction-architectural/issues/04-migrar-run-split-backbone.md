# 04 — Migrar `run_split` para o backbone

**What to build:** `cli/split.run_split` deixa de reimplementar as etapas iniciais do
pipeline (load_config → resolve → read_raw_csv → filtra período) e passa a usar o
backbone `measurement_source()` para obter rows pós-filtro e fieldnames.

O split tem requisitos próprios que o backbone deve acomodar sem perder semântica: a
checagem da coluna `Grupo_executor` antes de computar categorias, o cross-check de
`in_values` contra `real_values`, e a emissão de WARN de janela vazia e do log de
descarte por dataset bruto. A regra "WARN de janela vazia 1x por (órgão, arquivo bruto)"
deve ser preservada.

**Blocked by:** 02

**Status:** done

- [x] `run_split` usa `measurement_source()` para rows pós-filtro e fieldnames.
- [x] Checagem de `Grupo_executor` e cross-check `in_values` preservados.
- [x] WARN de janela vazia e log de descarte emitidos 1x por (órgão, arquivo bruto) como hoje.
- [x] Comportamento do split preservado — suíte de split verde (materialized e in-memory).

## Comments

- 2026-08-22 — Implementado. `run_split` chama `measurement_source(...,
  emit_period_filter_logs=False)` e reconstrói a condição "janela vazia"
  (`not rows and dropped_out_of_period + undated_dropped > 0`) para manter
  seu próprio `log_event` estruturado (orgao/competencia/inms/arquivo) —
  preferível ao log genérico do backbone porque nenhum outro chamador
  precisa desse contexto. `test_cli_split.py`: 18/18 verdes; suíte completa
  sem novas falhas.