# 02 - Criticidade dos campos da capa

Type: grilling
Status: resolved

## Question

Quais campos da capa são obrigatorios para processar, obrigatorios para publicar/assinar, ou opcionales — e qual o efeito de cada ausência (rascunho, bloqueio de publicação, ou irrelevante)?

Hoje `cli/report.py` só loga um `logger.info` quando `Valor mensal vigente` falta. Não há WARNING com criticidade e impacto quando competência, períodos, fiscais ou gestor estão ausentes. Por exemplo: MTur com 6 campos faltantes ainda produz relatório sem marcação de rascunho.

Decisões em aberto (o dono do domínio responde, pois algumas dependem de regra contratual):
- As três categorias, campo a campo: competência, períodos, fiscais, gestor, valor mensal, demais.
- Competência deve ser preenchida automaticamente a partir de `pyauditor run 2026-06`?
- Período inicial e final são derivables da competência?
- Relatório sem fiscais e gestor é formalmente válido?
- O arquivo gerado recebe marcação RASCUNHO / INCOMPLETO / NÃO PUBLICABLE?
- `run` deve retornar código de saída diferente de zero quando há campos obrigatorios ausentes? (depende do contrato de códigos — ticket 03.)

Contexto: review.md §2 (alta prioridade), seção "Perguntas que eu levaria para a equipe", cenários "Validação da capa".

## Answer

Resolvido por grilling (HITL). Os valores monetários saem da capa (migração CSV / ticket 07). A ausência de valor passa a "glosa não calculada" (ticket 01) e a critérios de código de saída (ticket 03).

1. As três categorias, campo a campo (assumindo monetários fora da capa; competência como argumento CLI):
   - Obrigatorios para publicar/assinar: Período inicial e final da aferição; Fiscais (técnico, administrativo, requisitante); Gestor do contrato; Situação geral diferente de "Em preenchimento". Também os campos comerciais de `capa.csv` (contrato, SEI, empresa, CNPJ, órgão, objeto, vigência) — documentales, necessários para publicar, não para processar.
   - Obrigatorios para processar: nenhum — o pipeline processa com capa incompleta e marca o resultado.
   - Opcionales/informativos: Número de OS, Número e Data de NF, Data da análise, Versão da planilha.
2. Competência: derivada do argumento CLI (`run 2026-06`); se a capa traz valor, deve coincidir (divergência = WARNING, leva ao ticket 03). Não bloqueia.
3. Períodos: derivables da competência (primeiro e último dia do mês); se a capa traz valores, validar coincidencia com o mês. Não bloqueia processar, mas são obrigatorios para publicar.
4. Fiscais e gestor: o relatório para publicação se marca como rascunho até nomear os 4 roles. Para processar, basta.
5. Marcação: existe estado "rascunho"/"não publicable" para capa incompleta. O mecanismo concreto fica em 03/04.
6. Código de saída: se decide em 03 (depende de 01/02). O conjunto de "pendências impeditivas" que 03 mapea é o desta lista (Q1–Q4).