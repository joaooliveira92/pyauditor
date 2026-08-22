# Mapa — Recuperação e evolução da suíte de testes do pyauditor

Label: wayfinder:map
Status: open

## Destination

A suíte de testes do pyauditor sai do vermelho (hoje: 33 falhas / 526 passam / 34 skips) e fica verde com o processo semanal do `python-testing-evolution` operante: reparo das costuras de string (regressão acidental), gate que impede a re-regressão, baseline e progresso persistidos (`.testing-progress/`), e workflow semanal de testes em CI. Gate de validação: pytest (cobertura `fail_under=85`), ruff, `ty` (perfil strict já configurado no mapa migracao-ty), bandit e pip-audit.

## Notes

-   Domain: pyauditor — pipeline de aferição do contrato 40/2022 (MinC/MTur), CLI que valida workbooks Excel por regras configuráveis (YAML→Pydantic→openpyxl).
-   Stack: Python 3.12+ + `uv`. Preservar o gerenciador e a stack de teste: `uv run --locked pytest`, pytest-cov, Hypothesis, Ruff, `ty`, bandit, pip-audit.
-   Comunicação e conteúdo de arquivos em **pt-BR** (CLAUDE.md — nunca espanhol).
-   Convocar sempre o skill **`python-testing-evolution`** em toda sessão que trabalhe os tickets deste esforço — o esforço é execução, não só decisão.
-   Processo do tracker: **claim** = setar `Status: claimed` no ticket ANTES de trabalhar; **resolve** = `## Answer` + `Status: resolved`, e [gist de 1 linha] + link no "Decisions so far" do mapa. Frontier = open + sem bloqueio + sem claim.

### Decisões da sessão de charting (grilling rodadas 1–2)

- Q1 (destino): reparo + processo — suíte verde **e** ciclo semanal operante (`.testing-progress`, notas, CI de testes).
- Q2 (base): usar a **working tree atual** (inclui o refactor em andamento, 157 arquivos modificados e sem commit) como base do esforço.
- Q3 (regressão): costuras de string sem espaço são **acidentais** — o texto deveria ter os espaços (ex. `ASCIIpositivo`, `doCSV` são quebrados).
- Q6 (mecânica do reparo): **script de uma passada** para as ~443 costuras identificadas + revisão por diff; casos ambíguos (junção intencional) revisados manualmente no ticket 03.
- Q7 (escopo do reparo): **consertar TODAS as 443** (defeito real, não só os 33 testes que quebram).
- Q8 (gate anti-regressão): **sim** — virar check de CI (regra Ruff/instrumento) para nunca mais voltar. Mecanismo exato é o ticket 02.
- Q4/Q9 (gate e CI): gate = **cadeia completa** (pytest + ruff + ty + bandit + pip-audit); CI de qualidade no escopo, **coordenado com o mapa `migracao-ty`** para não duplicar workflow; reparo é commit independente (separado do refactor).
- Q5/Q10 (afunilar cobertura): entrar como **not yet specified** — o skill prioriza risco, o teto de sinal cresce no ciclo semanal.

## Decisions so far

<!-- centraliza aqui, uma linha por ticket fechado: gist + link -->

- [01 — Que regra do Ruff detecta concatenação implícita de strings?](issues/01-ruff-rule-strings.md) — **Usar a família `ISC` do Ruff como gate anti-costura** (ISC001/ISC002/ISC003, estáveis, sem preview, compatíveis com ruff>=0.12), com `allow-multiline = false` para capturar o padrão multilinha da regressão; formatter funde literais que cabem na linha (auto‑prote); sem driver custom em pytest (Ruff já cobre sintaxe, tem `--fix` e integração de formatter). Findings em `notes/ruff-rule-strings.md`.
- [03 — Reparar as costuras de strings e deixar a suíte verde](issues/03-reparar-costuras.md) — **Suíte verde**: 559 passed / 34 skipped (era 16 failed / 543 passed), via 3 varreduras complementares (fronteira de concatenação + transição de caixa em literal já fundido + triagem de testes) — nenhum caso intencional de colagem sem espaço encontrado (`notes/casos-intencionais.md`); `ruff check`/`format --check` sem regressão frente ao baseline pré-existente.

## Not yet specified

-   **Elevar o sinal da suíte além do verde**: os 34 skips, a cobertura branch 89% (gate hoje 85), e os primeiros ciclos semanais do skill (Hypothesis nos parsers, integração real de openpyxl, rotas que o skill `python-testing-evolution` prioriza nos Stage 2–3). Forma-se por decisões semanais, então fica em fog.
-   **Relação exata do workflow semanal de testes com o workflow de qualidade do `migracao-ty`** (um workflow só vs separado; permissões read-only) — a definir no ticket 04, sabendo que `migracao-ty` já assume um workflow `ty` + `ruff` (+ pytest).

## Fora de escopo

-   **Completar/entregar o refactor em andamento** (157 arquivos, sem commit) — é trabalho em curso fora deste esforço; o abaste de costuras term solo.
-   **Mudar a base do verde para outro ponto** (ex. reverter a working tree a um commit) — não; assume-se a árvore atual.
-   **Alterar os arquivos de mapa/tickets de esforços anteriores** (arquivo do processo). Não mexer em `.scratch/migracao-ty/*`, exceto consulta de referência.
-   **Reescrever mensagens/semântica do corpus** além da restituição de espaços nas cost: o escopo é texto restaurado, não nova edição.