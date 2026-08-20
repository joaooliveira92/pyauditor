# Avaliação do Pipeline de Apuração do INMS 1.1

> **Nota de enquadramento:** esta avaliação adota uma abordagem inspirada em auditoria de controle externo, sem substituir manifestação oficial do Tribunal de Contas da União, da assessoria jurídica ou da autoridade competente.

## 1. Opinião preliminar

### Conclusão resumida

| Dimensão | Avaliação |
|---|---|
| Correção aritmética do índice | **Adequada** |
| Aderência literal da população à fórmula contratual | **Insuficientemente demonstrada** |
| Qualidade e integridade dos dados | **Parcialmente adequada** |
| Reprodutibilidade | **Parcialmente adequada** |
| Rastreabilidade e evidência | **Insuficiente** |
| Interpretação da pontuação | **Controversa, requer formalização** |
| Robustez dos testes | **Insuficiente** |
| Aptidão para fundamentar efeito financeiro | **Ainda não recomendável sem controles adicionais** |

A fiscalização técnica deve aferir quantidade, qualidade, tempo e modo da prestação em confronto com os indicadores contratuais, documentando irregularidades e eventual adequação do pagamento. O referencial do TCU diferencia a adequação do pagamento decorrente do nível de serviço das sanções administrativas propriamente ditas.

> **Opinião de auditoria:** o resultado de **97,7142857%** é matematicamente compatível com 171 ocorrências conformes em uma população de 175. Entretanto, não há evidência suficiente, apenas com os artefatos apresentados, de que essas 175 ocorrências correspondam integralmente ao conceito contratual de “total de incidentes abertos no período”, nem de que a regra de 20 pontos tenha natureza linear contínua.

## 2. Recálculo independente

Considerando como verdadeiros os quantitativos informados pelo pipeline:

$$
\text{INMS 1.1} = \frac{171}{175} \times 100 = 97{,}7142857143\%
$$

Déficit em relação à meta:

$$
98 - 97{,}7142857143 = 0{,}2857142857\text{ p.p.}
$$

Se, e somente se, a regra for linear contínua:

$$
165 + \left(\frac{0{,}2857142857}{0{,}1}\right)\times20
= 222{,}14285714
$$

Arredondado para duas casas:

$$
\boxed{222{,}14\text{ pontos}}
$$

Portanto:

- Numerador: **171**;
- Denominador: **175**;
- Resultado exato: **97,7142857%**;
- Resultado exibido: **97,71%**;
- Conformidade: **não conforme**;
- Pontuação linear contínua: **222,14 pontos**.

A conta está correta. O problema central não é aritmético, mas **semântico, contratual, probatório e metodológico**.

## 3. Achados de auditoria

### Achado 1. Risco de exclusão indevida de incidentes ainda não concluídos

#### Situação encontrada

O contrato define o denominador como “total de incidentes abertos no período”. Entretanto, o YAML exige:

```yaml
- type: not_null
  column: "DataHoraFim"
```

Isso significa que um incidente aberto no período, mas ainda não encerrado na data de extração, seria rejeitado antes do cálculo.

#### Efeito potencial

Esse controle pode produzir **viés de sobrevivência**:

- incidentes atendidos e encerrados permanecem;
- incidentes pendentes, potencialmente vencidos, são retirados;
- o percentual pode ficar artificialmente maior.

Matematicamente, o denominador contratual parece depender da abertura no período, não do encerramento. Portanto, um registro sem `DataHoraFim` pode ser exatamente uma ocorrência relevante para o denominador.

#### Avaliação

**Gravidade: alta.**

Mesmo que no arquivo específico não existam valores nulos, a regra é estruturalmente inadequada e pode contaminar competências futuras.

#### Recomendação

Não rejeitar automaticamente o registro do universo contratual por ausência de `DataHoraFim`. Em vez disso:

1. incluir no denominador todo incidente aberto no período;
2. classificar a situação na data de corte:
   - concluído no prazo;
   - concluído fora do prazo;
   - pendente com prazo ainda vigente;
   - pendente com prazo vencido;
3. definir contratualmente o tratamento dos pendentes ainda dentro do prazo no fechamento mensal;
4. impedir o fechamento definitivo da medição se a regra contratual não resolver esse caso.

Uma configuração conceitualmente mais segura teria separação entre população, validade e classificação:

```yaml
population:
  event_date_column: "DataHoraSolicitacao"
  event_date_rule: opened_in_period

validity:
  required_columns:
    - "Nº Solicitacao"
    - "DataHoraSolicitacao"
    - "DataHoraLimite"

classification:
  completed_at_column: "DataHoraFim"
  deadline_column: "DataHoraLimite"
```

`DataHoraFim` não deveria ser requisito para uma ocorrência pertencer à população de incidentes abertos.

### Achado 2. Ausência de definição explícita do período de competência

#### Situação encontrada

A apuração é mensal, mas o YAML não apresenta:

- data inicial;
- data final;
- coluna usada para inclusão no período;
- fuso horário;
- regra de fronteira;
- data e hora de corte da extração.

#### Risco

O pipeline pode selecionar registros:

- encerrados no mês, em vez de abertos no mês;
- abertos fora do mês e encerrados dentro dele;
- abertos na virada do mês com tratamento inconsistente;
- alterados retroativamente após a medição.

#### Recomendação

Registrar explicitamente:

```yaml
measurement:
  competence: "2026-06"
  population_date_column: "DataHoraSolicitacao"
  period_start: "2026-06-01T00:00:00-03:00"
  period_end_exclusive: "2026-07-01T00:00:00-03:00"
  extraction_cutoff: "2026-07-05T18:00:00-03:00"
  timezone: "America/Sao_Paulo"
```

A expressão recomendável para a fronteira é:

```text
period_start <= DataHoraSolicitacao < period_end_exclusive
```

Isso evita ambiguidade de frações de segundo no último dia do mês.

### Achado 3. O campo “No prazo” é aceito sem validação independente

#### Situação encontrada

O numerador depende diretamente do campo fornecido:

```yaml
numerator_filter:
  column: "No prazo"
  equals: "S"
```

O pipeline apenas verifica se o valor pertence ao conjunto `S` ou `N`.

#### Problema

O controle confirma a **forma**, mas não a **verdade material** do campo. Se a contratada ou o sistema de origem marcar um incidente vencido como `S`, o pipeline o aceitará.

#### Recomendação

Recalcular o indicador de prazo independentemente:

```text
recalculado_no_prazo =
    DataHoraFim não nula
    e DataHoraFim <= DataHoraLimite
```

Depois, confrontar:

```text
No prazo informado x No prazo recalculado
```

Qualquer divergência deve gerar uma ocorrência de auditoria identificada pelo número da solicitação. Se `DataHoraLimite` considerar calendários, pausas ou horários úteis, a origem e a imutabilidade desse campo também devem ser comprovadas.

### Achado 4. `count_distinct` não informa a chave de distinção

#### Situação encontrada

O YAML contém:

```yaml
aggregation: count_distinct
```

Mas não especifica a coluna usada para distinguir ocorrências.

#### Risco

O resultado pode variar conforme a implementação implícita, como contagem por linha inteira, número da solicitação, combinação de colunas, hash interno ou valor padrão do mecanismo.

#### Recomendação

Definir:

```yaml
calculation:
  shape: ratio
  aggregation: count_distinct
  distinct_key: "Nº Solicitacao"
```

Adicionar controles de chave não nula, tipo consistente, duplicidade, conflitos entre duplicatas, reabertura e tickets mesclados ou cancelados. Caso uma solicitação apareça em versões diferentes, a regra temporal deve ser formal e determinística.

### Achado 5. Escopo contratual não está sendo efetivamente demonstrado

#### Situação encontrada

O YAML registra:

```yaml
scope:
  contract: "40/2022 - Ministério da Cultura"
```

O CSV apresenta:

```text
40/2022 - Ministério Cultura
```

Há diferença de denominação. Também não foi demonstrada regra explícita de filtro por contrato, órgão, tipo de demanda, competência e catálogo abrangido.

#### Risco

Se o arquivo contiver múltiplos contratos ou tipos de demanda, registros estranhos ao INMS poderão ser incluídos.

#### Recomendação

Usar códigos canônicos:

```yaml
scope:
  contract_id: "40/2022"
  contract_aliases:
    - "40/2022 - Ministério Cultura"
    - "40/2022 - Ministério da Cultura"
  demand_type:
    equals_normalized: "INCIDENTE"
```

O pipeline deve demonstrar a formação da população, incluindo registros fora do contrato, fora da competência e de tipos diferentes.

### Achado 6. Distinção insuficiente entre população, elegibilidade, rejeição e erro de qualidade

#### Situação encontrada

A ROM informa apenas:

```text
Linhas lidas: 175
Linhas aceitas: 175
Rejeições: nenhuma
```

#### Problema

“Aceita” pode significar linha válida, ocorrência do contrato, ocorrência do período, integrante do denominador ou apta ao numerador.

#### Recomendação

Usar reconciliação formal:

```text
Linhas físicas lidas                         175
(-) Linhas malformadas                         0
(-) Registros de outros contratos              0
(-) Registros fora da competência              0
(-) Demandas que não são incidentes             0
(-) Duplicidades eliminadas                     0
(=) Incidentes abertos no período             175

Dos 175 incidentes:
  Concluídos no prazo                         171
  Concluídos fora do prazo                      4
  Pendentes com prazo vencido                   0
  Pendentes com prazo vigente                   0
```

A soma das classificações deve ser exatamente igual ao denominador.

### Achado 7. Possível contaminação dos dados por marcação HTML

#### Situação encontrada

No conteúdo apresentado, o cabeçalho e valores contêm elementos HTML, como:

```html
<strong data-lexical-text="true"> No prazo ;</strong>
```

Se essas tags existirem apenas na mensagem copiada, não há problema no CSV original. Se estiverem no arquivo processado, o resultado de 175 linhas aceitas é incompatível com o gate que admite somente `S` ou `N`.

#### Recomendação

Preservar o arquivo bruto e produzir evidência técnica de parsing:

- codificação;
- delimitador;
- nomes originais das colunas;
- nomes normalizados;
- amostra dos valores após parsing;
- quantidade de colunas por linha;
- hash do arquivo.

A remoção de HTML, caso necessária, deve ser registrada como transformação auditável, nunca silenciosa.

### Achado 8. Interpretação linear e contínua da pontuação não está suficientemente sustentada

#### Situação encontrada

O texto contratual estabelece “165 pontos mensalmente em caso de índice abaixo de 98% + 20 pontos a cada 0,1% abaixo da meta”. O YAML adotou interpretação linear contínua com base na redação de outro indicador.

#### Problema

A expressão admite pelo menos três leituras:

##### A. Linear contínua

$$
165 + \frac{0{,}285714}{0{,}1}\times20 = 222{,}14
$$

##### B. Apenas degraus completos

$$
165 + \left\lfloor\frac{0{,}285714}{0{,}1}\right\rfloor\times20 = 205
$$

##### C. Qualquer fração inicia novo degrau

$$
165 + \left\lceil\frac{0{,}285714}{0{,}1}\right\rceil\times20 = 225
$$

A diferença é material.

#### Avaliação

**Gravidade: alta.**

Não se recomenda transportar automaticamente uma fórmula do INMS 1.2 para o INMS 1.1, salvo se houver regra geral, remissão expressa, tabela confirmatória ou interpretação formal no processo.

#### Recomendação

Submeter a interpretação à gestão contratual e, se necessário, à assessoria jurídica, registrando decisão motivada. Até lá, a ROM deveria explicitar que a pontuação de 222,14 depende da interpretação linear contínua e que leituras alternativas resultariam em 205 ou 225 pontos.

### Achado 9. Uso potencialmente inadequado do termo “penalidade”

#### Situação encontrada

A saída registra:

```text
Penalidade: 222.14 pontos
```

#### Problema

Pontos de IMR ou INMS frequentemente constituem mecanismo de avaliação e adequação do pagamento, não necessariamente sanção administrativa. Os institutos devem ser diferenciados.

#### Recomendação

Verificar a terminologia contratual. Se os pontos alimentam uma tabela de glosa, preferir:

- pontuação apurada;
- efeito no IMR;
- adequação de pagamento;
- percentual de glosa contratual.

Reservar “penalidade” ou “sanção” ao processo sancionador, com competência, contraditório e rito próprios.

### Achado 10. Teste de aceitação circular

#### Situação encontrada

O próprio YAML contém o resultado esperado do conjunto real:

```yaml
acceptance_test:
  expected:
    numerator: 171
    denominator: 175
    result_pct: 97.71
    conforms: false
    penalty_points: 222.14
```

#### Problema

O teste garante apenas que o software reproduza um resultado conhecido. Não prova que fórmula, população, casos-limite, interpretação contratual ou origem dos dados estejam corretos. Configuração e resultado esperado no mesmo artefato também reduzem a independência do teste.

#### Recomendação

Criar testes independentes e orientados a propriedades:

1. 100 de 100 no prazo;
2. 98 de 100 no prazo, confirmando a igualdade da meta;
3. 97 de 100 no prazo;
4. incidente aberto no mês e pendente;
5. incidente aberto no mês anterior e encerrado no atual;
6. duplicidade do número da solicitação;
7. `No prazo = S` com fim posterior ao limite;
8. resultado exatamente 97,95%;
9. denominador zero;
10. valores como `s`, ` S ` ou `Sim`.

## 4. Problema de arredondamento

O pipeline exibe `97,71%`, mas calcula a pontuação com o valor integral. Isso é adequado, porém precisa ser explicitado. Se a pontuação fosse calculada sobre 97,71%, o resultado seria 223 pontos, e não 222,14.

Recomenda-se registrar:

```text
Resultado exato utilizado na comparação: 97,7142857143%
Resultado exibido, arredondado a duas casas: 97,71%
Regra de arredondamento: half-up
A conformidade e a pontuação foram calculadas antes do arredondamento.
```

A decisão de conformidade não deve usar valor previamente arredondado, salvo determinação contratual expressa.

## 5. Controles mínimos a adicionar

### Integridade do arquivo

- SHA-256 do arquivo bruto;
- nome original;
- tamanho em bytes;
- data e hora do recebimento;
- origem;
- responsável pela extração;
- versão do sistema de origem;
- codificação e delimitador;
- armazenamento imutável do original.

### Integridade estrutural

- quantidade esperada de colunas;
- cabeçalhos normalizados;
- chave primária;
- duplicidades;
- linhas quebradas;
- datas inválidas;
- colunas extras;
- tags HTML;
- espaços invisíveis;
- separador decimal e regionalização.

### Elegibilidade contratual

- número do contrato;
- período;
- tipo “Incidente”;
- unidades abrangidas;
- grupos executores abrangidos;
- exclusões previstas;
- chamados cancelados;
- chamados duplicados ou mesclados;
- reaberturas;
- indisponibilidades imputáveis à Administração;
- suspensões de SLA formalmente autorizadas.

### Validade temporal

- solicitação menor ou igual ao limite;
- fim maior ou igual à solicitação;
- comparação entre fim e limite;
- fuso horário;
- horários úteis e feriados;
- pausas de SLA;
- alterações retroativas.

### Reconciliação

- total do sistema de origem;
- total exportado;
- total lido;
- total elegível;
- total excluído;
- total rejeitado;
- total no denominador;
- numerador e complemento;
- soma das categorias igual ao total.

## 6. Modelo recomendado de ROM

```markdown
# Relatório de Ocorrências e Medição
## INMS 1.1 - Incidentes atendidos dentro do prazo

### 1. Identificação
- Contrato: 40/2022
- Órgão: Ministério da Cultura
- Competência: junho de 2026
- Data de corte: [data e hora]
- Data de processamento: [data e hora]
- Versão do pipeline: [versão/commit]
- Versão da configuração: [versão/commit]
- Hash SHA-256 do arquivo de entrada: [hash]

### 2. Critério contratual
- População: incidentes abertos no período
- Numerador: incidentes da população atendidos dentro do prazo
- Meta: resultado maior ou igual a 98%
- Fonte: Anexo D, Tabela 28, INMS 1.1

### 3. Reconciliação da população
- Linhas físicas lidas: 175
- Registros malformados: 0
- Fora do contrato: 0
- Fora da competência: 0
- Não classificados como incidente: 0
- Duplicidades: 0
- População contratual: 175

### 4. Classificação
- Concluídos no prazo: 171
- Concluídos fora do prazo: 4
- Pendentes com prazo vencido: 0
- Pendentes com prazo vigente: 0
- Total reconciliado: 175

### 5. Validações independentes
- Divergências entre “No prazo” informado e recalculado: 0
- Datas inconsistentes: 0
- Alterações posteriores ao corte: 0
- Ocorrências com suspensão de SLA: 0

### 6. Memória de cálculo
- Numerador: 171
- Denominador: 175
- Resultado exato: 97,7142857143%
- Resultado exibido: 97,71%
- Meta: >= 98,00%
- Situação: não conforme

### 7. Pontuação
- Déficit exato: 0,2857142857 ponto percentual
- Metodologia adotada: linear contínua
- Pontuação calculada: 222,14285714
- Pontuação exibida: 222,14

### 8. Ressalva interpretativa
A metodologia linear contínua depende da validação formal da interpretação
da expressão “20 pontos a cada 0,1% abaixo da meta”.

### 9. Ocorrências fora do prazo
[relação individualizada dos quatro chamados, com limite, fim e atraso]

### 10. Responsáveis
- Elaborado por:
- Revisado por:
- Fiscal técnico:
- Data:
```

## 7. Classificação das recomendações por prioridade

### Prioridade imediata, antes de produzir efeito financeiro

1. Corrigir a regra relativa a `DataHoraFim` nula.
2. Definir formalmente a população pela data de abertura.
3. Validar a interpretação linear da pontuação.
4. Recalcular “No prazo” a partir das datas.
5. Definir a chave do `count_distinct`.
6. Documentar competência, data de corte e fuso horário.
7. Preservar arquivo bruto e hash.
8. Produzir relação individualizada dos quatro incidentes fora do prazo.
9. Submeter o resultado ao contraditório contratual previsto.
10. Distinguir adequação de pagamento de eventual sanção.

### Prioridade alta

1. Criar reconciliação completa da população.
2. Implantar testes de casos-limite.
3. Controlar versão do YAML e do código.
4. Registrar parâmetros efetivamente executados.
5. Segregar elaboração e revisão da medição.
6. Gerar log imutável das transformações.

### Prioridade de aprimoramento

1. Assinatura digital da ROM.
2. Manifesto de execução em JSON.
3. Relatório comparativo mensal.
4. Alertas de desvio.
5. Amostragem documental dos chamados.
6. Trilha de retificações e reprocessamentos.

## 8. Encaminhamento sugerido

> A medição automatizada apurou índice de 97,7142857%, correspondente a 171 incidentes classificados como atendidos no prazo em uma população informada de 175 incidentes. A recomposição aritmética confirma o percentual apresentado. Contudo, antes da produção de efeitos financeiros, deverão ser saneadas ou formalmente justificadas: a definição da população com base nos incidentes abertos na competência; a situação dos registros sem data de conclusão; a validação independente do campo “No prazo”; a chave utilizada na contagem distinta; e a interpretação linear contínua da regra de acréscimo de 20 pontos a cada 0,1% abaixo da meta. Até o saneamento, o resultado deve ser tratado como preliminar.

## 9. Conclusão final

O pipeline tem uma **boa base estrutural**, com configuração declarativa, controles de qualidade, memória de cálculo e teste de aceitação. Isso favorece padronização e reprodutibilidade.

Por outro lado, os controles atuais validam principalmente a **consistência formal dos dados**, e não ainda sua **completude, exatidão, origem, elegibilidade contratual e verdade material**. O maior risco é o pipeline gerar um número matematicamente correto sobre uma população juridicamente incorreta.

$$
\boxed{\text{Resultado aritmético correto, mas evidência ainda insuficiente para conclusão financeira definitiva}}
$$

## Referências consultadas

- Tribunal de Contas da União. **Fiscalização técnica e recebimento provisório**. Disponível em: <https://licitacoesecontratos.tcu.gov.br/6-1-4-fiscalizacao-tecnica-e-recebimento-provisorio-2/>.
- Tribunal de Contas da União. **Súmula TCU 269**, sobre vinculação da remuneração em serviços de TI a resultados ou níveis de serviço. Disponível em: <https://pesquisa.apps.tcu.gov.br/redireciona/sumula/SUMULA-EJURIS-28921>.
- Tribunal de Contas da União. **Aquisições de TI**. Disponível em: <https://portal.tcu.gov.br/tecnologia-da-informacao/aquisicoes-de-ti-1>.
