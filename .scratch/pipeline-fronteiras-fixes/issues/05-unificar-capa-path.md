# 05 — Unificar resolução de `capa_path` entre `bootstrap` direto e `run`/interativo

**Origem:** [Orchestration↔cli/interactive boundary review](../../pipeline-fronteiras-review/issues/03-orchestration-cli-interactive-boundary.md)

**What to build:** `_capa_path_for` está duplicado com lógica divergente entre `cli/main.py` e `orchestration/run.py`. Com os mesmos flags (`--capa-path meucapa.csv --orgao MinC`), `pyauditor bootstrap` direto ignora o nome customizado e grava em `capa_MinC.csv`, enquanto `pyauditor run`/interativo respeita `meucapa.csv`. Extrair uma única função de resolução de `capa_path`, usada por ambos os entry points, garantindo que o mesmo conjunto de flags produza sempre o mesmo caminho de arquivo.

**Blocked by:** None — can start immediately.

- [ ] `pyauditor bootstrap --capa-path X --orgao Y` e `pyauditor run --capa-path X --orgao Y` (ou o fluxo interativo equivalente) resolvem para o mesmo caminho de arquivo
- [ ] Existe uma única implementação de resolução de `capa_path`, sem duplicação entre `cli/main.py` e `orchestration/run.py`
- [ ] Teste de regressão comparando os dois entry points com os mesmos flags
