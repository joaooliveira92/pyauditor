# Abas financeiras da planilha de inspiração — aferição Junho/2026

## Fonte

- Planilha real: `inspiration-spreadsheet/afericao_06_2026.xlsx` (17 abas), inspecionada com openpyxl 3.1.5 (modos `data_only=False` e `data_only=True`).
- Documento de contraste: `docs/spreadsheet.md` (plano da estrutura mensal).
- Objetivo: documentar o que o futuro passo `consolidate` (2.1) precisa reproduzir nas abas financeiras.

## Ordem das abas (tal como aparecem no workbook)

1. `CAPA_E_CONTROLE`
2. `LEIA_ME`
3. `CADASTROS`
4. `SERVICOS_POR_ORGAO`
5. `INMS_BASE`
6. `ATENDIMENTO_N1`
7. `MONITORAMENTO_NOC_SOC`
8. `ATENDIMENTO_N2`
9. `OPERACAO_N3`
10. `EVIDENCIAS`
11. `GLOSAS`
12. `CALCULO_PAGAMENTO`
13. `CHECKLIST_FISCAL`
14. `RELATORIO_FISCAL`
15. `PAINEL_GERENCIAL`
16. `HISTORICO`
17. `FONTES_E_PREMISSAS`

Todas as abas levam no canto superior direito um bloco `VERSÃO 1.0 | EM ANÁLISE` e uma linha `Execução 18/08/2026 | Dados: 49 dias | Responsável: Maria Aparecida Gomes`.

---

## 1. `CAPA_E_CONTROLE` — painel de identificação

Região de rótulos (col. A) + valores (col. B), de A1 a B27. É o painel de controle do relatório; aqui está o **valor mensal** que alimenta o cálculo.

| Coordenadas | Rótulo | Valor |
|---|---|---|
| A1 | MEMÓRIA DE CÁLCULO — AFERIÇÃO INMS | (título) |
| A3/B3 | Número do Contrato | 40/2022 |
| A4/B4 | Processo SEI | 72031.010172/2020-97 |
| A5/B5 | Empresa Contratada | CENTRAL IT TECNOLOGIA DA INFORMAÇÃO S/A |
| A6/B6 | CNPJ da Contratada | 07.171.299/0001-96 |
| A7/B7 | Órgão Contratante | Ministério da Cultura |
| A9/B9 | Vigência | 09/12/2022 a 09/12/2026 |
| A10/B10 | Competência | Junho/2026 |
| A11–12 | Período inicial/final da aferição | 01/06/2026 / 30/06/2026 |
| A13–15 | Número OS / Nota Fiscal / Data NF | `PREENCHER` (pendentes) |
| A16 | Fiscal Técnico | Maria Aparecida Gomes |
| A17–19 | Fiscal Requisitante / Administrativo / Gestor | `PREENCHER` (pendentes) |
| **A20/B20** | **Valor Mensal Vigente** | **481534.8** (numérico) |
| A21/B21 | Valor Global Anual | 5778417.64 (numérico; = mensal × 12) |
| A23/B23 | Status do Controle | `EM ANÁLISE` |
| A27/B27 | Situação Geral da Aferição | `Conforme com glosa` |
| A29–A35 | Avisos da geração | Mensagens `[ATENÇÃO]` por campos não preenchidos (fiscal requisitante, administrativo, gestor, NF, seguro, OS) |

**Campo financeiro chave para o cálculo:** `B20` (Valor Mensal Vigente = 481.534,80) é o mesmo que `CADASTROS!B45` e alimenta `CALCULO_PAGAMENTO!B6` e o `Valor Base` de `GLOSAS`. `B21` (`Valor Global Anual`) = 12 × mensal.

---

## 2. `SERVICOS_POR_ORGAO` — matriz de segregação

Matriz fixa de 9 serviços (linhas 4–12) com 6 colunas (A–F), linha 3 = cabeçalhos. **Não é numérica; é uma matriz booleana de segregação.**

| Col | Cabeçalho | Significado |
|---|---|---|
| A | Item | 1..9 |
| B | Serviço | nome do serviço |
| C | Prestado ao MinC? | `Sim` |
| D | Prestado ao MTur? | `Sim` |
| E | Segregação Obrigatória? | `Sim` |
| F | Critério de Rateio | `Chamados, ativos ou valor definido` |

**Serviços (todas as linhas com `Sim`/`Sim`/`Sim`/`Chamados, ativos ou valor definido`):**
1. Central de Serviços e Monitoramento
2. Gerenciamento Técnico das Operações e Projetos
3. Banco de Dados
4. Aplicações, Virtualização e Computação em Nuvem
5. Serviços Corporativos
6. Armazenamento e Backup
7. Redes
8. Segurança da Informação
9. DevOps

Dimensão observada: **por serviço** (9 serviços contratuais, todos prestados a ambos os órgãos, todos com segregação obrigatória). O critério de rateio é textual (`Chamados, ativos ou valor definido`) e coincide com o `docs/spreadsheet.md` (§ cadastros: 9 serviços).

---

## 3. `GLOSAS` — registro de ocorrências com impacto financeiro

Registro tabular de **9 ocorrências** (linhas 4–12) com cabeçalhos na linha 3. Há, ainda, um **resumo financeiro** nas linhas 15–20.

### Cabeçalhos (linha 3, A–P)

| Col | Cabeçalho |
|---|---|
| A | Competência |
| B | Órgão |
| C | Item Contratual |
| D | Serviço |
| E | Indicador |
| F | Resultado |
| G | Meta |
| H | Faixa de Descumprimento |
| I | Percentual de Ajuste |
| J | Valor Base |
| K | Valor Glosa |
| L | Reincidência |
| M | Justificativa |
| N | Número da Ocorrência |
| O | Decisão Fiscal |
| P | Observação do Gestor |

### Linhas representativas (valores atuais)

| Órgão | Indicador | Resultado | Meta | Faixa de Descumprimento | % Ajuste | Valor Base | Valor Glosa |
|---|---|---|---|---|---|---|---|
| MinC | 1.2 | 93.97 | 95 | Déficit de 1.03pp | 0.8667 | 481534.8 | 4173.32 |
| MinC | 1.4 | 98.95 | 99.5 | Déficit de 0.55pp | 5.5 | 481534.8 | 26484.41 |
| MinC | 1.7 | 2.46 | 77 | Déficit de 74.54pp | 19.385 | 481534.8 | 93345.47 |
| MinC | 1.11 | 49.39 | 5 | Acima da meta em -44.39pp | 2.2195 | 481534.8 | 10687.71 |
| MinC | 1.12 | 81.5 | 95 | Déficit de 13.5pp | 3.374 | 481534.8 | 16246.89 |
| MinC | 1.14 | 95.01 | 99.5 | Déficit de 4.49pp | 11.225 | 481534.8 | 54052.28 |
| MTur | 1.2 | 97.96 | 100 | Déficit de 2.96pp | 1.2222 | 481534.8 | 5885.41 |
| MTur | 1.11 | 55.09 | 5 | Acima da meta em -50.09pp | 2.5046 | 481534.8 | 12060.38 |
| MTur | 1.12 | 89.82 | 95 | Déficit de 5.18pp | 1.2957 | 481534.8 | 6239.20 |

Dimensão observada: **por indicador** e **por órgão** (coluna `B` = MinC/MTur). Não há coluna de serviço preenchida nestas linhas (as colunas `C` `Item Contratual` e `D` `Serviço` estão vazias aqui).

### Fórmulas inferidas dos valores (verificadas aritmeticamente)

- **Valor Glosa por linha** (col K) = `Valor Base × % Ajuste / 100`. Verificação: 481.534,80 × 0,008667 ≈ 4.173,32; × 0,055 = 26.484,41; × 0,19385 = 93.345,47; etc.
- **% Ajuste** (col I) é um valor numérico (não é fórmula); relaciona-se com o déficit de descumprimento, mas a planilha não traz a tabela de conversão completa (ver `CADASTROS` abaixo).

### Resumo da Glosa (linhas 15–20)

| Rótulo | Valor |
|---|---|
| Total de Pontos | 47592.63 |
| Fórmula | `47592.63 x 0,001 = 47.5926%` |
| Limite | `30.0%` |
| Percentual Aplicado | `30.0000%` |
| Valor Glosa | 144460.44 |

- `Total de Pontos` (47592.63) = **soma da coluna I (% de Ajuste) × 1000** (0.8667+5.5+19.385+2.2195+3.374+11.225+1.2222+2.5046+1.2957 = 47.5927 ≈ 47.59263).
- **Aplicação da glosa:** pontos × 0,001 → percentual de ajuste (47.59%), limitado pelo teto de 30% → 30% × Valor Mensal (481.534,80) = **144.460,44**.

> Nota: o `Total de Pontos` nesta aba e o `D14` de `CALCULO_PAGAMENTO` são **valores introduzidos/congelados manualmente, não fórmulas vivas** que liguem a linha I da mesma aba. A relação indicador→pontos→glosa não está automatizada neste workbook (ver `CALCULO_PAGAMENTO` e `CADASTROS`).

---

## 4. `CALCULO_PAGAMENTO` — cálculo do pagamento da competência

Aba em 4 blocos: **Parâmetros de Entrada** (linhas 5–9), **Tabela de Componentes MinC/MTur/Consolidado** (linhas 11–17), **Manifestação financeira** (linhas 20–21), **Valor global anual** (linha 23).

### Parâmetros de Entrada (linhas 5–9) — células editáveis

| Célula | Rótulo | Valor |
|---|---|---|
| A6 | Valor mensal vigente após 5º Termo de Apostilamento | `B6` = 481.534,8 |
| A7 | Limite máximo de glosa (%) | `B7` = 0.3 (=30%) |
| A8 | Rateio MinC | `B8` = 0.5 |
| A9 | Rateio MTur | `C9` = 0.5 |

> `A2` informa que **o rateio MinC/MTur é entrada do fiscal** até que se indique a fonte oficial (advertência reproduzida em `LEIA_ME!A21`).

### Tabela de Componentes (linhas 11–17) — colunas B (MinC), C (MTur), D (Consolidado)

| Linha | Rótulo | MinC (B) | MTur (C) | Consolidado (D) |
|---|---|---|---|---|
| 11 | Componente | `MinC` | `MTur` | `Consolidado` |
| 12 | Percentual de rateio | `=$B$8` (0.5) | `=$C$9` (0.5) | `=$B$12+$C$12` (=1.0) |
| 13 | Valor bruto | `=$B$6*B12` | `=$B$6*C12` | `=$B$6*D12` |
| 14 | Pontos de glosa | 0 | 0 | **47592.63** (valor numérico; o mesmo que `GLOSA!B16`) |
| 15 | Valor da glosa | 0 | 0 | `=MIN(D14*0.001,$B$7*100)/100*D13` |
| 16 | Outros ajustes | 0 | 0 | 0 |
| 17 | Valor recomendado | `=MAX(0,B13-B15-B16)` | `=MAX(0,C13-C15-C16)` | `=MAX(0,D13-D15-D16)` |

**Cálculos inferidos (verificados com `data_only=True`):**

- `D13` (bruto consolidado) = 481.534,8 × 1,0 = 481.534,8.
- `D15` (valor da glosa) = `MIN(47592.63×0.001, 0.3×100)/100 × 481534.8` = `MIN(47.5926, 30)/100 × 481534.8` = `0.30 × 481534.8` = **144.460,44** (coincide com `GLOSA!B20`).
- `D17` (valor recomendado) = `MAX(0, 481534.8 − 144460.44 − 0)` = **337.074,36** (coincide com `RELATORIO_FISCAL!B32`).

### Linha 23

`Valor global anual` = `=$B$6*12` → 481.534,8 × 12 = 5.778.417,60.

**Campo financeiro chave:** `B6` (valor mensal) = `CAPA_E_CONTROLE!B20` = `CADASTROS!B45`. A glosa final depende de `B7` (limite 30%) e `D14` (pontos de glosa, introduzido manualmente).

---

## 5. `CADASTROS` — parâmetros que sustentam o cálculo (referência cruzada)

Aba de parâmetros; traz as regras que **base** do cálculo financeiro:

- **Órgãos (A3–A5):** `MinC`, `MTur`.
- **Serviços contratuais (A13–D23):** 9 linhas, unidade `VAL/MES`, quantidade mensal 1, fonte `Contrato e TR` (coincide com os 9 de `SERVICOS_POR_ORGAO`).
- **Indicadores INMS (A25–K40):** tabela com os campos `Código`, `Descrição`, `Meta`, `Sentido`, `Periodicidade`, `Base de Pontuação`, `Passo`, `Pontos por Passo`, `Fórmula de Medição`, `Fonte`, `Observação`. Cada indicador (1.1 a 1.14) com sua meta, sentido e parâmetros de pontos. Fonte: `TR - Tabela 28`.
- **Regras de Glosa (A42–B45):**
  - `A43/B43`: Fórmula → **`Ajuste_NMS(%) = Pontos x 0,001`**
  - `A44/B44`: Limite Máximo → **30%**
  - `A45/B45`: Valor Mensal → **481.534,80**

### Relação pontos→% (inferida e verificada)

A coluna `Percentual Glosa` de `INMS_BASE` (col V) e `% Ajuste` de `GLOSAS` (col I) verificam, para os indicadores com `Pontos por Passo` definido:

- `1.4` (déficit 0.55pp, passo 0.1, pontos/passo 1000): (0.55/0.1)×1000×0.001 = **5.5%** ✓
- `1.7` (déficit 77.54, passo 1, pontos/passo 250): 77.54×250×0.001 = **19.385%** ✓
- `1.11` (déficit 44.39→ resultado 49.39, passo 1, pontos/passo 50): 44.39×50×0.001 = **2.2195%** ✓ (MinC)
- `1.12` (déficit 13.5, passo 0.1, pontos/passo 25): (13.5/0.1)×25×0.001 = **3.375%** ✓
- `1.14` (déficit 4.49, passo 0.1, pontos/passo 250): (4.49/0.1)×250×0.001 = **11.225%** ✓

**Estado: `1.2` não segue essa relação com a tabela (0 pontos/0.1pp na tabela; o próprio `CADASTROS!K28` indica *"15 pontos/0,1 p.p.; a deletar por prioridade quando houver detalhamento"*); o seu `% Ajuste` (0.8667) é, portanto, uma **entrada manual/ajuste por prioridade**, não dedutível das colunas do cadastro. Isso confirma que a conversão não está totalmente automatizada para todos os indicadores.**

---

## 6. Dimensões e estruturas observadas (por órgão vs por indicador vs por serviço)

- **Por órgão (MinC/MTur):** coluna `Órgão`/`B` em `INMS_BASE`, `GLOSAS` e `RELATORIO_FISCAL`. Valores observados: `MinC`, `MTur`, `Consolidado` e `Compartilhado` (indicadores telefônicos 1.11/1.12 e disponibilidade 1.4/1.5/1.14 com dado compartilhado, sem segregação técnica).
- **Por indicador:** código `INMS` em `INMS_BASE`/`GLOSAS`/`CADASTROS`; cada indicador com uma linha por órgão.
- **Por serviço:** `SERVICOS_POR_ORGAO` (matriz 9×serviço); `CADASTROS` lista os 9 serviços; em `INMS_BASE` há colunas `Serviço` (C) e `Grupo Operacional` (D), embora nas linhas do mês de junho a coluna `Serviço` **esteja vazia** (só `Grupo Operacional` aparece preenchida, e.g. `Atendimento Remoto N1`, `Monitoramento NOC/SOC`, `Atendimento Presencial N2`, `Operação e Sustentação N3`).
- **Não:** o plan não automatiza o fluxo indicador→pontos→glosa final; `CALCULO_PAGAMENTO` usa `D14` (pontos de glosa) como valor introduzido, e `GLOSAS` o `Total de Pontos` como valor transversal.

---

## 7. Implicação para o passo `consolidate` (2.1)

Para reproduzir o cálculo de pagamento, `consolidate` deve reconstruir:

1. **Agregação por órgão:** para cada indicador `INMS`, consolidar MinC + MTur (soma de numeradores/denominadores, exceto indicadores de disponibilidade que usam média/fórmula específica — ver `docs/spreadsheet.md`).
2. **Detecção de glosas:** para cada linha indicador×órgão, se `resultado` < meta (ou > meta para meta `<`), marcar ocorrência. Produzir `GLOSAS` com `Resultado`, `Meta`, `Faixa`, `% Ajuste`, `Valor Base`, `Valor Glosa`.
3. **`% Ajuste` = `(déficit / passo) × pontos por passo × 0.001`, com teto 30%**, salvo para indicadores com regra manual (1.2) e indicadores compartilhados que exigem decisão do fiscal.
4. **`CALCULO_PAGAMENTO`:** `valor mensal` (CAPA!B20) × rateio (parâmetro fiscal, 0.5/0.5 provisório) = `bruto`; `glosa` = `MIN(pontos × 0.001, 30%) × bruto`; `recomendado` = `MAX(0, bruto − glosa − outros ajustes)`.
5. **`SERVICOS_POR_ORGAO`:** matriz de 9 serviços com flags MinC/MTur/segregação (geralmente `Sim`).
6. **`CAPA_E_CONTROLE`** fornece `valor mensal` (B20) e `Valor Global Anual` (B21 = ×12); `LEIA` registra a advertência de rateio provisório 50/50.

**O ponto de entrada manual (pontos de glosa) é o maior limite de automatização atual:** o workbook não computa os pontos a partir dos indicadores; recebe-os como entrada.