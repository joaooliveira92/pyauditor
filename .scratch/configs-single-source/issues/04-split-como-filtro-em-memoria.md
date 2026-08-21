# 04 — Split como filtro lógico em memória (eliminar `_split/` físico e YAMLs derivados)

**What to build:** a segmentação por Categoria deixa de materializar arquivos. `split` vira função pura que filtra linhas em memória usando `categoria_filter.compute_categoria_values`; `measure` itera categorias filtrando `rows` sem escrever `input/_split/<inms>/<categoria>.csv` nem `configs/*/inms-*.*.yaml`. I/O de INMS segmentados cai ~60% e `input/` volta a conter só dado de entrada.

**Blocked by:** 02 — Single-source: `configs/_shared/` + loader com injeção de órgão

**Status:** done

- [x] `cli/split.py:run_split` refatorado para modo `in_memory=True` (ou nova função `filter_rows_by_categoria`) que retorna `dict[categoria, list[rows]]` sem `atomic_write`; `_write_filtered_csv`/`_write_derived_config` removidos do caminho padrão (ou mantidos atrás de flag `--materialize` para debug)
- [x] `cli/measure.py:run_measure` atualizado para, quando `categorias.yaml` declara `grupo_executor` para o INMS, medir cada categoria filtrando `rows` em memória via `compute_categoria_values` + `read_raw_csv` (uma leitura do CSV bruto), gerando um ROM por categoria (`INMS-01.ATENDIMENTO_N1` etc.) sem depender de CSVs pré-gerados
- [x] `input/<orgao>/<AAAA>/<MM>/_split/` não é mais criado em `run` normal; `sintetico.xlsx` continua sendo gerado via `excel/sintetico.py` lendo `categorias.yaml` + CSV bruto (sem `_split/`)
- [x] `uv run pyauditor run 2026-06 --orgao both` produz os mesmos ROMs/Excel que antes (diff de `roms/` e `reports/` vazio para 06/2026) e `ls input/MinC/2026/06/_split` não existe após run limpo
- [x] Teste de não-regressão para `outros` contábil: linhas com `Grupo_executor` não mapeado continuam contadas e gerando warning, sem entrar no cálculo de conformidade
