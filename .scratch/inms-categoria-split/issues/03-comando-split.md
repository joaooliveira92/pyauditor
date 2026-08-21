# 03 — `pyauditor split`: CSVs filtrados + configs derivadas

**What to build:** o novo comando standalone `pyauditor split <competência> --orgao <MinC|MTur>`
(`docs/spec/inms-pipeline.md` §14.3), no mesmo padrão dos comandos existentes (`bootstrap`/
`measure`/`report`/`consolidate`: uma função `run_split`, um `check_split_ready`, um arquivo
`src/pyauditor/cli/split.py`).

Para cada par (INMS, categoria) em `mode: grupo_executor` de `categorias.yaml` (ticket 01), `split`
materializa em disco:

- **CSV filtrado**: `input/<orgao>/<ano>/<mes>/_split/<inms>/<categoria>.csv`.
- **Config de indicador derivada**: `configs/<orgao>/inms-<n>.<categoria>.yaml` — copia
  `quality_gates`/`calculation`/`target`/`penalty` do `inms-<n>.yaml` base, muda só `id` e
  `source.csv` (nunca `source.dataset` — `split` não toca em `datasets.yaml`). O ponto extra no nome
  (`inms-<n>.<categoria>.yaml`) deixa a config gitignored e descoberta pelo glob não-recursivo já
  existente de `measure` (`discover_config_files`) sem nenhuma mudança em `measure`. Ver ADR
  [0002](../../../docs/adr/0002-config-por-categoria-gerada-pelo-split.md).

`catch_all_contains` é resolvido em tempo de execução: lê os valores literais de `Grupo_executor`
presentes no CSV bruto daquela competência/órgão, subtrai os já reivindicados por `in_values` de
outras categorias do mesmo INMS/órgão, e o resto vira o filtro efetivo.

`outros` gera só o CSV filtrado (`outros.csv`, auditoria — mesma pasta `_split/<inms>/`), sem config
derivada. Quando `outros` tiver linhas, `split` emite (ticket 07 do mapa de decisões):

```
WARNING: INMS 1.1 (MinC/2026-06), categoria outros: 3 linha(s) não classificada(s) em nenhuma categoria — revisar categorias.yaml
```

INMS em `mode: whole_indicator` são pulados inteiramente por `split` (nem CSV, nem config derivada).
`split` sempre sobrescreve ao rerodar (idempotência por regeneração; o CSV bruto original nunca é
tocado).

**Blocked by:** 01

**Status:** resolved

- [x] `pyauditor split <competência> --orgao <MinC|MTur>` roda como comando standalone (ainda não
      precisa estar em `run` — isso é o próximo ticket)
- [x] Para cada INMS/categoria em `mode: grupo_executor`, gera o CSV filtrado e a config derivada nos
      caminhos exatos acima
- [x] `catch_all_contains` resolvido corretamente contra os literais reais do CSV bruto, excluindo os
      já reivindicados por outras categorias do mesmo INMS
- [x] `outros.csv` sempre gerado (mesmo vazio), sem config derivada correspondente
- [x] `WARNING` de `outros > 0` emitido com o texto exato acima
- [x] `mode: whole_indicator` não produz nenhum artefato de `split`
- [x] Rerodar `split` sobre o mesmo bruto sobrescreve sem erro (idempotência)
- [x] Depois de `split`, `measure` (sem nenhuma mudança de código) descobre e mede as configs
      derivadas via o glob já existente
- [x] `uv run mypy --strict src` e `uv run pytest` verdes
