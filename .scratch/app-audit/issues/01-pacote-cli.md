# 01 — Análise SRP do pacote cli

Type: research
Status: resolved
Blocked by: —

## Question

Analisar o pacote `src/pyauditor/cli/` (main.py 737, measure.py 684, split.py 439, report.py 263, consolidate.py 187, bootstrap.py 127, results.py 121, run.py 63, dependencies.py 26) e os módulos de raiz vinculados `codes.py` e `atomic_write.py` sob a lente de SRP do spec: responsabilidades misturadas, God Objects, inicializadores/comandos que concentram orquestração, validação, persistência e transformação. Classificar cada candidato (CRÍTICA..NÃO RECOMENDADA) com evidências precisas (arquivo/função/linha), fato vs. hipótese, e propor plano por arquivo conforme spec.md.

Considerar como dimensão os testes `tests/test_cli_*.py` (measure 542, report 584, consolidate 523, split 379, run 196, bootstrap 94, main 360, dependencies 56) — cobertura e dificuldade de isolamento.

Deliverable: artefato com a nota SRP do pacote `cli` (arquivo `.scratch/app-audit/notes/pacote-cli.md`, criado dentro deste tick), mais o resumo classificado num  `## Answer` com os candidatos priorizados.

## Answer

Candidatos do pacote `cli/` por prioridade (nota completa com evidências
arquivo:linha e plano por arquivo: `.scratch/app-audit/notes/pacote-cli.md`):

- **CRÍTICA — `cli/measure.py`**: `run_measure` (measure.py:123-637) é função God
  (515 linhas físicas, cc≈41 por AST) com responsabilidades de I/O, validação,
  serialização e apresentação; duplica regra de categoria com `split.py` 
  (fallback `_shared`, `per_inms`, cross-check `in_values`, warning de `outros`);
  cobertura da suíte 77% (mais baixa do pacote; ramos de erro da expansão a
  descoberto).
- **ALTA — `cli/main.py`**: 737 linhas, três responsabilidades distintas no mesmo
  arquivo (schema do parser L222-364; request dataclasses + tradutores L74-456;
  dispatch + orquestração multi-órgão + logging L463-729); orquestração duplicada
  com `orchestration/run.py`; cobertura 92% reduz o risco.
- **ALTA — `cli/split.py`**: `run_split` (split.py:145-439) 295 linhas, cc ≈ 40;
  mistura filtragem de dados, escrita CSV/YAML, cross-check (idêntico ao de
  `measure`) e apresentação de `sintetico.xlsx` (conhece camada Excel).
- **MÉDIA — `cli/report.py`**: `run_report` (report.py:110-263, cc ≈ 20) orquestra
  8 fontes de dados (capas, equipe, objetos, configs, histórico, ROMs) e a
  política de publicação 3/4.
- **BAIXA — `cli/consolidate.py`**: orquestração fina (cc ≈ 12, cobertura 89%);
  mover `_load_common_capa` para `excel/capa.py` é melhoria opcional.
- **NÃO RECOMENDADA**: `bootstrap.py`, `results.py` (hub de imports), `run.py`
  (thin), `dependencies.py` (registry) e os módulos de raiz `codes.py` /
  `atomic_write.py` — coesos; dividir fragmentaria sem ganho.

Achado principal: a duplicação de regra de categoria entre `measure` e `split` é
o maior ganho de SRP do pacote — consolidar o cross-check e o warning de `outros`
em `categoria_filter.py` (já declarado como fonte única) é o primeiro passo.