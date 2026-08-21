# 08 — Tornar `read_existing_decisions` resiliente a renomeação leve de header

**Origem:** [Excel report→consolidate boundary review](../../pipeline-fronteiras-review/issues/05-excel-report-consolidate-boundary.md)

**What to build:** `read_existing_decisions` (`excel/consolidate.py`) faz lookup de coluna de decisão por nome exato; `_check_no_duplicate_headers` só detecta duplicatas, não renomeações/typos. Um fiscal que renomeie levemente um cabeçalho de decisão (ex.: espaço extra, acento) perde essa decisão inteira no próximo `consolidate`, em silêncio total. Adicionar detecção explícita: se um cabeçalho esperado não é encontrado mas existe um candidato próximo (normalização de espaço/acento/case), falhar com erro nomeando os dois nomes em vez de simplesmente não achar a coluna. Corrigir também o docstring do módulo, que afirma ler o `.xlsx` de `report.py` quando na verdade `consolidate` nunca abre esse arquivo (capa vem de `capa.csv`, indicadores vêm do ROM JSON) — e remover a variável morta `report_paths` em `cli/consolidate.py` que reforça essa leitura errada.

**Blocked by:** None — can start immediately.

- [ ] Um cabeçalho de decisão renomeado/com espaço extra gera erro acionável nomeando o cabeçalho esperado e o encontrado, em vez de perder a decisão silenciosamente
- [ ] Docstring de `excel/consolidate.py` reflete a fonte real dos dados (capa.csv + ROM JSON, não o `.xlsx` de `report.py`)
- [ ] Variável morta `report_paths` removida de `cli/consolidate.py`
- [ ] Teste de regressão cobrindo o cabeçalho renomeado
