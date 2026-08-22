# Map: app-audit — auditoria SRP do código Python

Label: wayfinder:map

## Destination

Um relatório técnico em Markdown (`.scratch/app-audit/report.md`) seguindo fielmente as 6 seções e o formato de saída de `.scratch/app-audit/spec.md`: analisa recursivamente todos os `*.py` do repositório, classifica cada candidato (CRÍTICA..NÃO RECOMENDADA) com evidências, e propõe planos por arquivo. Nenhum código é modificado — entrega é só o relatório.

## Notes

- Domínio: repositório `pyauditor` — pipeline de aferição do contrato 40/2022 (MinC/MTur). Pipeline Python 3.12, tipagem estrita (mypy strict), `ruff`, `pytest` + cobertura.
- Spec de referência: `.scratch/app-audit/spec.md` (deve ser lido integralmente por cada sessão antes de escolher o ticket).
- Skill de referência: `.agents/skills/python-production-engineer/SKILL.md` — chamar via Skill tool sempre que um ticket pedir análise/refatoração.
- Sempre que os tickets precisarem de grilling/domain-modeling, chamar as skills `grilling` e `domain-modeling`.
- Todos os textos e comentários em pt-BR. Nunca em espanhol (erro duro).
- Ferramentas disponíveis: `ruff`, `mypy`, `pytest` (suite 506 passando). `radon`/`xenon` não instalados — usar `ast` e análise estática e registrar essa limitação no relatório.
- Um ticket por pacote de produção + um ticket de síntese. Testes são dimensão dentro de cada ticket de pacote. Módulos de raiz dobrados nos pacotes afins: `codes`/`atomic_write`→cli; `categoria_filter`→engine; `logging`/`capa_paths`→orchestration. `periodo.py` mora na raiz e é analisado no ticket do engine (não deve ser movido — inverte dependências). Tickets 01–07 produzem a nota `.scratch/app-audit/notes/pacote-<pacote>.md`; 08 = síntese.
- O relatório final é fiél ao formato do spec: 6 seções, classificação por prioridade, plano incremental e comandos exatos de validação.
- Limitação de sessão: nunca resolver mais de um ticket por sessão, exceto tickets `research` (podem ser resolvidos em paralelo por subagentes).
- O spec exige referências precisas (arquivo, classe, função, linha) e diferenciação de fato observado vs. hipóte.

## Decisions so far

- [01 — Análise SRP do pacote cli](.scratch/app-audit/issues/01-pacote-cli.md) — `measure.py` CRÍTICA (run_measure God, cc≈41), `main.py` e `split.py` ALTA; duplicação de regra de categoria entre measure/split → consolidar em `categoria_filter.py`. Nota: `.scratch/app-audit/notes/pacote-cli.md`.
- [02 — Análise SRP do pacote config](.scratch/app-audit/issues/02-pacote-config.md) — único candidato `models.py` MÉDIA (bloco acceptance test, consumido só por testes → mover a `config/acceptance.py` com reexport); demais NÃO RECOMENDADA. Nota: `.scratch/app-audit/notes/pacote-config.md`.
- [03 — Análise SRP do pacote engine](.scratch/app-audit/issues/03-pacote-engine.md) — `pipeline.py` ALTA (5 responsabilidades; split em loading/discovery/version com reexport); `precomputed_table.py` e leitores CSV duplicados MÉDIA; `periodo.py` fica na raiz (não mover). Nota: `.scratch/app-audit/notes/pacote-engine.md`.
- [04 — Análise SRP do pacote excel](.scratch/app-audit/issues/04-pacote-excel.md) — `inms_1_1_audit.py` (1332) e `sintetico.py` (970) CRÍTICA; `consolidate.py` ALTA; extração mecânica via costuras naturais (`_write_section_*`, renderers por shape) com API preservada por facade. Nota: `.scratch/app-audit/notes/pacote-excel.md`.
- [05 — Análise SRP do pacote interactive](.scratch/app-audit/issues/05-pacote-interactive.md) — `flow.py` ALTA (extrair `interactive/{fields,commands,status_view}.py`); `provider.py` MÉDIA; acoplamento real é com orchestration (não excel/config). Nota: `.scratch/app-audit/notes/pacote-interactive.md`.
- [06 — Análise SRP do pacote orchestration](.scratch/app-audit/issues/06-pacote-orchestration.md) — `run.py` (1109) CRÍTICA (plan.py + command_dispatch.py + resume.py); `logging.py` e `summary.py` ALTA; `state.py` e `capa_paths.py` coesos. Nota: `.scratch/app-audit/notes/pacote-orchestration.md`.
- [07 — Análise SRP do pacote rom](.scratch/app-audit/issues/07-pacote-rom.md) — `render.py` MÉDIA (recalcula domínio na apresentação; extrair `penalty_interpretation()` para a engine); hipótese "lê a fonte e renderiza" refutada. Nota: `.scratch/app-audit/notes/pacote-rom.md`.
- [08 — Síntese e relatório final](.scratch/app-audit/issues/08-sintese-e-relatorio-final.md) — relatório final em um único doc `.scratch/app-audit/report.md` (6 seções conforme spec); ranking por faixa de prioridade e retorno; comandos exatos de validação; limitação radon/xenon registrada. Fecha o mapa — sem tickets restantes.

## Not yet specified

_Vazio — síntese (ticket 08) decidiu o formato do relatório e manteve o critério de cobertura via notas por pacote; nada mais a especificar dentro do escopo.

## Out of scope

- **Não** executar nenhuma alteração/refatoração de código — o spec ordena explicitamente "não modifique nenhum arquivo".
- Não instalar dependências novas (`radon`, `xenon`) sem necessidade — registro apenas como limitação.