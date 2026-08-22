# 08 — Síntese e relatório final

Type: task
Status: resolved
Blocked by: 01, 02, 03, 04, 05, 06, 07

## Question

Consolidar as 7 notas por pacote (artefatos `notes/pacote-*.md`, vinculados aos tickets 01–07) no relatório final `.scratch/app-audit/report.md`, seguindo fielmente o formato de saída do spec.md: 6 seções — Resumo executivo, Ranking dos candidatos, Plano sugerido por arquivo, Falsos positivos e arquivos grandes aceitáveis, Plano incremental, Validações recomendadas.

Decisões a fechar nesta resolução (síntese, HITL):
- montar o relatório em um único doc `.scratch/app-audit/report.md` (padrão) vs. fragmentado;
- ordem final dos candidatos no ranking (interseção das notas por prioridade);
- comandos exatos de validação (ruff, mypy --strict, pytest) para os steps planejados;
- coletar e registrar limitações (radon/xenon não instalados — baseada em ast/análise estática).

## Answer

Decisões de síntese (HITL, fechadas com o dono do esforço em 2026-08-22):
1. **Relatório único**: `.scratch/app-audit/report.md` (padrão do spec/mapa), um só doc com as 6
   seções exigidas. Não fragmentar.
2. **Ranking**: faixa de prioridade (CRÍTICA → BAIXA) e, dentro dela, por retorno esperado (linhas
   físicas desc., pior complexidade primeiro). Seção 2 lista apenas CRÍTICA/ALTA/MÉDIA/BAIXA; os
   NÃO RECOMENDADA e o dado `anexo_e.yaml` ficam só na seção 4 e no resumo por contagem.
3. **Comandos exatos de validação** (pyproject: `mypy strict`, `ruff`, `pytest`+`--cov-branch` gate
   85%): documentados na seção 6 do relatório. Ferramentas confirmadas no ambiente
   (.venv: ruff 0.16.3, mypy 2.3.1, pytest 9.1.1, Python 3.12.13).
4. **Limitações registradas**: `radon`/`xenon` não instalados — toda cc é aproximada (AST/McCabe
   simplificado); equivalência byte-exata de .xlsx pós-extração declarada como hipótese a validar;
   branch coverage completa exige a suíte do projeto.

Resultado final: **`.scratch/app-audit/report.md`** (544 linhas, 6 seções na ordem do spec:
Resumo executivo · Ranking dos candidatos · Plano sugerido por arquivo · Falsos positivos e arquivos
grandes aceitáveis · Plano incremental · Validações recomendadas). Consolidou as 7 notas por pacote
(`notes/pacote-*.md`) com referências `arquivo:linha` e distinção fato vs. hipótese. Nenhum código de
produção foi modificado.

Com a síntese, o mapa fica sem tickets — o esforço de planejamento termina aqui; a entrega
(report.md) é o passo seguinte e não gera novos tickets.