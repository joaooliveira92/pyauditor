# 01 — Modelo de Categoria/Grupo executor: escopo e semântica

Type: grilling
Status: resolved

## Question

Cada INMS deve ser segmentado por `categoria`, derivada de um filtro sobre a coluna `Grupo_executor` já presente no CSV bruto do fornecedor. Antes de especificar o mapeamento completo e a mecânica de pipeline, era preciso fechar a semântica: o que é uma categoria, como ela se relaciona com o engine existente (`docs/spec/inms-pipeline.md`, "1 YAML+CSV = 1 indicador = 1 medição"), o que fazer com linhas que não batem em nenhuma categoria, e qual o novo artefato de saída pedido (planilha "sintética").

## Answer

Resolvido via sessão de grilling (16 perguntas, todas aprovadas pelo usuário) + verificação factual num CSV real (`input/MinC/2026/06/inms-01.csv`).

1. **Papel no pipeline**: `categoria`/`Grupo_executor` é uma etapa de **filtragem pré-engine**. O CSV bruto do fornecedor (já filtrado só por período+INMS) é recortado em N CSVs, um por categoria; cada um alimenta o pipeline `measure` existente sem nenhuma mudança de shape (`ratio`/`segmented_ratio`/etc.) nem de meta contratual — a meta continua a mesma do Anexo D para as categorias substantivas.

2. **Um INMS pode pertencer a N categorias** — o subconjunto de categorias válidas varia por INMS, não é fixo (ex.: INMS 1.1 está em 3 categorias; INMS 1.3 e 1.14 só em "Operação e Sustentação"). Cada categoria de um INMS gera **uma medição independente** (seu próprio ROM) — N categorias = N ROMs para aquele INMS/competência.

3. **Categoria "Operação e Sustentação da Infraestrutura de TI" é catch-all por regra literal**: captura todo `Grupo_executor` que contém a substring `(CIT)` e não está nas listas explícitas das outras categorias daquele INMS. Não é uma terceira lista fechada de strings.

4. **4ª categoria `outros`** (decisão introduzida pelo usuário depois da checagem factual): captura as linhas cujo `Grupo_executor` **não** contém `(CIT)` e não bate com nenhuma categoria substantiva (ex.: `Executores CODIN/SEI`, achado real no CSV de INMS 1.1/2026-06). É puramente contábil — contada, mas não entra no cálculo de conformidade/meta. Existe pra garantir que nenhuma linha do dataset do fornecedor desapareça sem explicação.

5. **Categoria sem linhas no período é normal**: gera medição com população zero (mesmo tratamento de quality gate "zero-atividade" já existente no engine), não trava o pipeline. Achado real: INMS 1.1/2026-06 não tem nenhuma linha `(CIT/MINC) - 1º Nível`, então "Atendimento Remoto aos Usuários" mediria população zero naquele mês.

6. **Mapeamento categoria→Grupo_executor→INMS mora num arquivo declarativo separado** (schema e nome exatos ficam para ticket próprio), consumido por uma etapa nova e explícita no CLI — recomendação aprovada: um passo tipo `split` que materializa os CSVs filtrados em disco antes do `measure`, que continua inalterado (auditável: dá pra inspecionar o CSV filtrado antes de medir).

7. **Novo artefato de saída**: além dos ROMs Markdown (um por categoria), um **xlsx sintético por INMS** — distinto do Excel final consolidado já especificado (`docs/spec/inms-pipeline.md`/`docs/spreadsheet.md`) — com uma linha por valor único de `Grupo_executor` daquele INMS (categoria como coluna). Detalhes de layout/colunas ficam para ticket próprio (prototype).

8. **Mapeamento das 3 categorias substantivas dadas pelo usuário → abas do Excel final já existentes**: `Atendimento Remoto aos Usuários`→`ATENDIMENTO_N1`, `Atendimento Presencial ao Usuário`→`ATENDIMENTO_N2` (RJ/BDB como sub-linhas via coluna `Grupo_executor`, mesma aba), `Operação e Sustentação da Infraestrutura de TI`→`OPERACAO_N3`. `MONITORAMENTO_NOC_SOC` fica fora desta rodada (nenhum mapeamento de categoria fornecido pra ela — fog).

9. **Diretiva de categorias fornecida pelo usuário** (fonte de verdade para o ticket de mapeamento declarativo), com a linha malformada `INMSs: 1.1, 1` da categoria "Atendimento Presencial ao Usuário" descartada (mantida só `1.1, 1.2, 1.6, 1.7, 1.9`):

   - **Atendimento Remoto aos Usuários** — Grupo_executor: `(CIT/MINC) - 1º Nível` — INMSs: 1.1, 1.2, 1.6, 1.7, 1.11, 1.12, 1.13
   - **Atendimento Presencial ao Usuário** — Grupo_executor: `(CIT/MINC) - 2º Nível`, `(CIT/MINC) - 2º Nível/RJ`, `(CIT/MINC) - 2º Nível/BDB` — INMSs: 1.1, 1.2, 1.6, 1.7, 1.9
   - **Operação e Sustentação da Infraestrutura de TI** — Grupo_executor: catch-all "contém (CIT), não é nenhum dos grupos acima" — INMSs: 1.1, 1.2, 1.3, 1.6, 1.7, 1.9 (1.14 removido desta lista — ver item 11)

10. ~~INMS fora da diretiva original (1.8, 1.10) ficam como fog~~ — resolvido no item 14 abaixo: não têm categoria.

Terminologia (`Categoria`, `Grupo executor`, `Categoria "outros"`, ajuste em `ROM`) já registrada em `CONTEXT.md`.

## Atualização — categoria MONITORAMENTO_NOC_SOC (indicador inteiro, sem Grupo_executor)

11. **Categoria `MONITORAMENTO_NOC_SOC`** (4ª categoria substantiva, mapeando pra aba homônima do Excel final): aplica-se a **INMS 1.4** (disponibilidade de sistema crítico), **1.5** (disponibilidade de sistema não-crítico) e **1.14** (índice de disponibilidade de serviços de infraestrutura). Diferente das outras categorias, esses datasets são um único registro pré-agregado por indicador (achado do esforço anterior, ticket 13) — **não têm coluna `Grupo_executor`**, então a categorização é do **indicador inteiro**, sem filtro linha-a-linha e sem etapa `split`: o `measure` lê o registro pré-agregado direto e o resultado inteiro é rotulado `MONITORAMENTO_NOC_SOC`.

12. **1.14 sai da lista de "Operação e Sustentação da Infraestrutura de TI"** (estava na diretiva original, item 9) — como seu dataset não tem `Grupo_executor`, não pode ser filtrado por essa categoria; passa a pertencer só a `MONITORAMENTO_NOC_SOC`.

13. **1.8 e 1.10 continuam fog** quanto a categoria — nenhuma das duas variantes (filtro por `Grupo_executor` ou indicador inteiro) foi especificada pra eles ainda.

## Atualização — 1.8/1.10 sem categoria; ausência de dataset = "não ativado" (regra geral do engine)

14. **INMS 1.8** (Ocorrências de Desconformidade Técnica) e **INMS 1.10** (Taxa de implantação de controles de segurança) **não possuem categoria** — não é fog, é uma decisão: esses indicadores não se encaixam no modelo Categoria/Grupo executor (nem filtro por `Grupo_executor`, nem "indicador inteiro" rotulado numa categoria como `MONITORAMENTO_NOC_SOC`). Item 13 acima fica superado por esta decisão.

15. **Ausência de dataset de entrada = "não ativado", não erro — regra geral do engine, não específica de 1.3/1.8/1.10.** Se o CSV de um INMS não existir para uma competência, o pipeline não deve tratar isso como falha de quality gate nem como dado incompleto: significa que aquele elemento contratual simplesmente não foi demandado/ativado no período. Isso vale para qualquer um dos 14 indicadores, não uma lista fechada — 1.3 (Quantidade de projetos atendidos dentro do prazo), 1.8 e 1.10 são citados como os candidatos mais prováveis na prática (indicadores "sob demanda"), não os únicos possíveis.

16. **Essa ausência precisa ficar explícita em dois lugares**: (a) na execução do `pyauditor` (log/saída do CLI deve deixar claro que o indicador foi pulado por ausência de dataset, não silenciosamente ignorado); (b) no relatório xlsx (ver ticket 04) — o INMS ausente ainda aparece no relatório, com uma frase tipo `"Esse serviço não foi requisitado no período selecionado"` em vez de linhas de dados ou um erro. O texto exato e onde ele aparece no layout do xlsx ficam para o ticket 04.

## Atualização — item 9 substituído pelo ticket 02

17. **A diretiva de categorias do item 9 acima foi substituída** por uma diretiva completa e final fornecida pelo usuário na sessão do [ticket 02](02-mapeamento-declarativo.md) — inclui a categoria `Operação e Sustentação` com 1.6/1.9/1.14 adicionados, e resolve (com dados reais de MinC e MTur) os casos em que o INMS listado numa categoria não tem `Grupo_executor` no CSV real (1.6 no MinC, 1.9, 1.11, 1.12, 1.13). Ver ticket 02 para a lista INMS↔categoria definitiva e o schema `categorias.yaml`. A semântica geral deste ticket (papel de filtro pré-engine, N categorias = N medições, `outros` contábil, catch-all por regra literal) continua valendo inalterada.
