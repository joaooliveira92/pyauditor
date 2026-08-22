# 04 — Análise SRP do pacote excel

Type: research
Status: resolved
Blocked by: —

## Question

Analisar o pacote `src/pyauditor/excel/` (inms_1_1_audit.py 1332, sintetico.py 970, consolidate.py 722, report.py 685, orgao_consolidation.py 432, objetos.py 326, capa.py 208, _style.py 178, equipe.py 148, glosas.py 138, groups.py 118, inms_base.py 96, _workbook.py 60, _datetime.py 39, prazos.py 28, _csv_verbatim.py 27, _safety.py 36) com lente de SRP do spec — provável maior concentração de God Objects e multi-responsabilidades (leitura, cálculo, serialização) em inms_1_1_audit (1332), sintetico (970). Não tratar arquivos grandes automaticamente como problema: usar evidências de coesão/acoplamento. Isso é a base do deliverável principal da auditoria; detalhe as divisões propostas.

Considerar igualmente os testes `tests/test_excel_*.py` e `test_inms_1_1_audit.py` (876).

## Answer

Candidatos e prioridade (detalhe em `.scratch/app-audit/notes/pacote-excel.md`):

- **CRÍTICA** — `inms_1_1_audit.py` (1332/1100 lógicas): maior arquivo do repo; concentra regra de prazo, validação de qualidade, resolução de grupos e serialização das 9 seções; 10 funções >40 linhas, `_write_raw_block` cc=16; API pública é só `has_required_columns`/`write_sheet` → extração por seções para subpacote `inms_1_1/` com facade preservada (testes `test_inms_1_1_audit.py`, 876 linhas/25 testes, devem passar sem edição).
- **CRÍTICA** — `sintetico.py` (970/767): dispatcher `write_sintetico_workbook` de 253 linhas (cc=32) + renderers por shape + abas verbatim + estatísticas puras; 24 imports (engine/config/atomic_write). Extrair `_stats`, `_verbatim_sheets` e renderers em `sintetico/_sheets/`.
- **ALTA** — `consolidate.py` (722/553): `build_glosas` 144 linhas (cc=18) mistura dedup, decisão fiscal, rateio e escrita; `read_existing_decisions` (cc=16) faz I/O+validação. Extrair `_decisions_io` e `_glosa_calcs`.
- **MÉDIA** — `report.py` (685/479): coeso por aba; só mover `compute_report_glosa` e validações inline.
- **BAIXA** — `capa.py` (CSV × render), `glosas.py` (domínio × histórico I/O), `_style.py`.
- **NÃO RECOMENDADA** — `orgao_consolidation.py` (432, domínio puro), `objetos.py`/`equipe.py` (parsers de um CSV), e utilitários pequenos.

Validação: `ruff` (265 erros pré-existentes E501/S101), `mypy` limpo, subconjunto excel com 169 testes passando; `radon`/`xenon` indisponíveis — usada análise `ast` própria. Nenhum código modificado.