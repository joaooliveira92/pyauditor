# 06 — Documentação, ADR, limpeza final e `quality_gate` `unique` opcional

**What to build:** a migração fica registrada e o repo limpo. Nova ADR explica single-source vs alternativas (incluindo Alternativas B/C descartadas), `CONTEXT.md`/`docs/spec/inms-pipeline.md` atualizados, e um terceiro `QualityGateCheck` `unique` (opcional) valida `id_column` duplicado antes do `count_distinct`.

**Blocked by:** 05 — Discovery determinístico + teste de não-regressão

**Status:** done

- [x] ADR `docs/adr/0003-configs-single-source-por-orgao.md` criada: contexto (duplicação MinC/MTur + derivados trackeados), decisão (single-source + filtro em memória), alternativas consideradas (B: `!include`/herança, C: builder em Python), consequências (clone determinístico, -28 arquivos, `split` sem I/O)
- [x] `CONTEXT.md` e `docs/spec/inms-pipeline.md` §§2-4 atualizados: `configs/_shared/` como fonte, `órgão` como dimensão de execução, `split` como filtro lógico, `acceptance_test` em `tests/`
- [x] Limpeza final: `configs/MinC/inms-*.yaml` e `configs/MTur/inms-*.yaml` deletados (se ainda existirem como shim), `input/_split` removido de `.gitignore` se obsoleto, `README.md` atualizado com novo layout
- [x] (Opcional, vertical completo) `config/models.py` ganha `UniqueCheck(type="unique", column: str)` + `engine/quality_gates.py` valida duplicatas de `id_column` como `RejectedRow` antes do cálculo; teste sintético cobre duplicata
- [x] `uv run zensical build --clean` (se aplicável) e `uv run pytest --cov` mantêm cobertura ≥85%
