# 05 — Análise SRP do pacote interactive

Type: research
Status: resolved
Blocked by: —

## Question

Analisar o pacote `src/pyauditor/interactive/` (flow.py 559, provider.py 436) com lente de SRP do spec: flow como orquestrador do modo interativo, provider como integração com infraestrutura de entrada/prompt. Procurar mistura de lógica de UI, validação, transformação de dados e orquestração; candidatos a extração, acoplamento com excel/config. Evidências precisas por candidato, classificação e plano de divisão compatível com API pública.

Considerar testes correspondentes (ex.: `tests/test_interactive_*.py`) e dificuldade de isolamento.

## Answer

Candidatos (detalhe em `notes/pacote-interactive.md`):

1. **`flow.py` — ALTA** (559 físicas / 140 stmts): 5 motivos independentes de mudança (formulário, catálogo/política de comandos, apresentação de estado, contrato com orquestração, tradução de falha). Maiores funções: `collect_answers` (206–315, 110 fís), `_run_guided_flow`+callbacks `on_failure`/`on_state_change` (482–552, 78 fís), `select_commands` (318–385, 68 fís). Sem God Object; extração em `interactive/{fields,commands,status_view}.py` preservando `__all__`.
2. **`provider.py` — MÉDIA** (436 físicas, coeso): adapter Questionary/Rich; complexidade concentrada em `ask_multi_choice` (297–367, CCM≈14) e `ask_choice` (259–295, CCM≈8); validação de contrato duplicada 4× e resposta de quebra `show_summary` — extrair helpers intra-arquivo, sem novo módulo.
3. **`__init__.py` — NÃO RECOMENDADA** (13 linhas; import TTY-gated em `cli/main.py:698`).

Achados-chave: **não há acoplamento com `excel`/`config`** (grep in `interactive/` vazio) — o contrato real é com `orchestration.run/state/summary` e `periodo.month_bounds`; string mágica `"dependência não satisfeita:"` viaja de `run.py:1011` a `flow.py:64/443–454` (débito, requer mudança em `orchestration`); mapeamento estado→ícone duplica `summary.py:69–80`. Testes: 11 passam (mypy ok; ruff só E501/I001 pré-existentes); cobertura própria flow 71% / provider 56% — `on_failure` (retry/skip/abort), `_force_commands_for` e validações de contrato sem teste; razão do fluxo (flow.py:126–201) depende de `os.chdir` global + `bootstrap_capa_csv` (acoplamento filesystem/excel) → sinal #12 do spec.

Análise com `ast` puro (radon/xenon indisponíveis — limitação registrada; CCM simplificada sem `and`/`or` em curto-circuito).