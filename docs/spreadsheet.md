# Plano para criação da planilha Excel de aferição técnica

Estruturei o plano considerando que a planilha será um instrumento mensal de aferição, cálculo de glosas e manifestação do fiscal técnico, com segregação obrigatória entre **MinC** e **MTur** em todos os serviços nos quais houver prestação para ambos os órgãos.

## 1. Objetivo da planilha

Criar uma pasta de trabalho mensal que permita ao fiscal técnico:

1. registrar as evidências da execução;
2. separar os resultados do **Ministério da Cultura** e do **Ministério do Turismo**;
3. calcular os Indicadores de Níveis Mínimos de Serviço (INMS);
4. identificar descumprimentos;
5. calcular glosas ou ajustes no pagamento;
6. consolidar os resultados por serviço contratual;
7. emitir uma manifestação técnica favorável, favorável com glosa ou desfavorável ao pagamento;
8. manter rastreabilidade entre os valores apresentados e os documentos comprobatórios.

O contrato adota pagamento fixo mensal vinculado ao atendimento dos níveis mínimos de serviço. O Termo de Referência estabelece que a obtenção dos resultados condiciona o pagamento integral e que o não atingimento pode gerar glosas ou sanções.

### Documentos para conferência técnica

- Estão disponíveis dentro de dados/relatorios.

---

O documento de aferição de junho de 2026 já apresenta evidências separadas para MinC e MTur em diversos indicadores de Atendimento Remoto N1, Monitoramento NOC/SOC, Atendimento Presencial N2 e Operação e Sustentação N3.

Essa separação será transformada em dados estruturados, e não mantida apenas em imagens ou blocos textuais.

### Regra de cálculo do consolidado

O consolidado não será, por padrão, uma média simples entre os percentuais dos dois órgãos.

Sempre que os quantitativos estiverem disponíveis, será calculado da seguinte forma:

$$
\text{Resultado consolidado}
=
\frac{\text{Numerador MinC} + \text{Numerador MTur}}{\text{Denominador MinC} + \text{Denominador MTur}}
$$

Isso evita distorção quando os órgãos possuem volumes de chamados muito diferentes.

### Exceção

Para indicadores de disponibilidade calculados por ativo ou serviço, o consolidado deverá seguir a fórmula específica prevista no Termo de Referência.

Quando forem usadas médias, a planilha indicará:

- quantidade de ativos do MinC;
- quantidade de ativos do MTur;
- média de cada órgão;
- método de ponderação;
- resultado consolidado.

---

## 3. Estrutura proposta da pasta de trabalho

### Aba 1: `CAPA_E_CONTROLE`

Será a página inicial e o painel de identificação do relatório.

#### Campos

- número do contrato;
- processo SEI;
- empresa contratada;
- CNPJ da contratada;
- órgão contratante atual;
- competência;
- período inicial e final da aferição;
- número da Ordem de Serviço;
- número da nota fiscal;
- data de emissão da nota fiscal;
- fiscal técnico;
- fiscal requisitante;
- fiscal administrativo;
- gestor do contrato;
- valor mensal vigente;
- versão da planilha;
- data da análise;
- situação geral da aferição.

> **Preenchimento automatizado (spec `competencia-cli-equipe`)**: competência e
> os períodos de aferição são derivados do argumento `--competência` da CLI —
> nunca hand-fill. Fiscal técnico, fiscal requisitante, fiscal administrativo e
> gestor do contrato vêm de `input/equipe.csv` (fonte única dos responsáveis,
> criada pelo `pyauditor bootstrap`). Os demais campos seguem hand-fill nos
> CSVs de capa (`capa.csv` / `capa_<órgão>.csv`).

#### Situações possíveis

- Em preenchimento;
- Aguardando evidências;
- Em análise;
- Conforme;
- Conforme com glosa;
- Não conforme;
- Aprovado para pagamento;
- Não recomendado para pagamento.

### Aba 2: `CADASTROS`

Concentrará os parâmetros que não devem ser digitados repetidamente.

#### Cadastros previstos

- órgãos: MinC e MTur;
- contrato e processo;
- empresa e CNPJ;
- lista dos nove serviços;
- grupos operacionais;
- códigos dos indicadores;
- metas;
- sentido de avaliação;
- fórmulas;
- regras de glosa;
- responsáveis;
- tipos de evidência;
- classificações de conformidade;
- parâmetros da competência.

#### Serviços que compõem o objeto contratual

1. Central de Serviços e Monitoramento;
2. Gerenciamento Técnico das Operações e Projetos;
3. Banco de Dados;
4. Aplicações, Virtualização e Computação em Nuvem;
5. Serviços Corporativos;
6. Armazenamento e Backup;
7. Redes;
8. Segurança da Informação;
9. DevOps.

### Aba 3: `INMS_BASE`

Essa será a principal base de dados da aferição.

Cada linha representará a seguinte combinação:

```text
Competência + grupo operacional + indicador + órgão
```

#### Exemplo

```text
Junho/2026 + Atendimento Remoto N1 + INMS 1.2 + MinC
Junho/2026 + Atendimento Remoto N1 + INMS 1.2 + MTur
```

#### Colunas propostas

1. competência;
2. item contratual;
3. serviço;
4. grupo operacional;
5. código INMS;
6. descrição;
7. órgão;
8. meta mínima ou máxima;
9. sentido da meta;
10. numerador;
11. denominador;
12. resultado calculado;
13. unidade;
14. aplicabilidade;
15. resultado esperado;
16. conformidade;
17. diferença para a meta;
18. ocorrência de glosa;
19. percentual de glosa;
20. valor-base;
21. valor da glosa;
22. justificativa;
23. referência da evidência;
24. número SEI;
25. responsável pela evidência;
26. observação do fiscal.

#### Indicadores identificados na aferição de junho

- **INMS 1.1:** incidentes atendidos dentro do prazo;
- **INMS 1.2:** requisições atendidas dentro do prazo;
- **INMS 1.3:** projetos atendidos dentro do prazo;
- **INMS 1.4:** disponibilidade de sistema ou serviço crítico;
- **INMS 1.5:** disponibilidade de sistema ou serviço não crítico;
- **INMS 1.6:** eficácia no tratamento de chamados;
- **INMS 1.7:** satisfação dos usuários;
- **INMS 1.9:** tempo médio de implementação de mudança;
- **INMS 1.10:** implantação de controles de segurança;
- **INMS 1.11:** chamadas telefônicas abandonadas;
- **INMS 1.12:** chamadas atendidas em até 20 segundos;
- **INMS 1.13:** chamados atendidos diretamente pelo Nível I;
- **INMS 1.14:** disponibilidade dos serviços de infraestrutura.

### Aba 4: `ATENDIMENTO_N1`

Apresentará os resultados do atendimento remoto nos blocos **MinC**, **MTur**, **Consolidado** e **Análise do fiscal**.


| Item | Indicadores | Meta | Glosa | Aferição da empresa conforme Relatório | Aferição dos fiscais* | Resultado | Pontuação de Penalidade |
|---|---|---|---|---|---|---|---|
| INMS 1.1 | Quantidade de incidentes atendidos dentro do prazo | >= 98% | (Total de incidentes atendidos dentro do prazo / Total de incidentes abertos no período) x 100 | 165 pontos (mensalmente em caso de índice abaixo de 98%) + (20 pontos a cada 0,1% abaixo da meta). | N/A | N/A | Alcançado 0 |
| INMS 1.2 | Quantidade de requisições atendidos dentro do prazo | >= 95% | (Total de requisições atendidas dentro do prazo conforme tipo de prioridade) / Total de requisições abertas no período conforme tipo de prioridade) x 100 | Prioridade Alta: 20 pontos a cada 0,1% abaixo da meta Prioridade Média: 15 pontos a cada 0,1% abaixo da meta Prioridade Baixa: 10 pontos a cada 0,1% abaixo da meta | 98,46% | 98,65% | Alcançado 0 |
| INMS 1.6 | Eficácia no tratamento de chamados (requisições e incidentes) | >= 97% | Total de chamados atendidos - Total de chamados reabertos) / Total de chamados atendidos | 200 pontos a cada 0,5% abaixo da meta | 98,48% | 100% | Alcançado 0 |
| INMS 1.7 | Satisfação dos usuários | >= 80% | (Total de Avaliações Positivas - "Satisfeitos" e "Muito Satisfeitos") / Quantidade total | 250 pontos a cada 1% abaixo da meta | 100% | 100% | Alcançado 0 |
| INMS 1.11 | Índice de chamadas telefônicas abandonadas | <=5% | (Total de chamadas telefônicas abandonadas / Total de chamadas telefônicas) | 50 pontos a cada 1% acima da meta | 2,49% | 1,89% | Alcançado 0 |
| INMS 1.12 | Índice de chamadas telefônicas atendidas em até 20 (vinte) segundos | >=95% | (Total de chamadas telefônicas atendidas em até 20 segundos / Total de chamadas telefônicas) | 25 pontos a cada 0,1% abaixo da meta | 95,35% | 95,49% | Alcançado 0 |
| INMS 1.13 | Índice de chamados atendidos no Nível I (Apurar a porcentagem de chamados que são atendidos diretamente pelo nível I) | Será acordado com a CONTRATADA uma taxa a ser aferida de acordo com o que é ideal conforme preconizado pelo ITIL. A revisão do indicador ocorrerá trimestralmente, no intuito de aumentar a quantidade de chamados atendidos em nível I | 50 pontos a cada 1% abaixo da meta acordada. | 100% | 100% | Alcançado | 0 |
| PONTUAÇÃO TOTAL | | | | | | | 0 |

------------------------------

Os indicadores telefônicos deverão informar se a central é compartilhada e se os dados podem ser segregados por órgão. Se a fonte não fornecer a separação, a limitação será registrada expressamente, sem misturar o resultado compartilhado com os resultados exclusivos.

### Aba 5: `MONITORAMENTO_NOC_SOC`


| Item | Indicadores | Meta | Glosa | Aferição da empresa conforme Relatório | Aferição dos fiscais | Resultado | Pontuação de Penalidade |
|---|---|---|---|---|---|---|---|
| INMS 1.4 | Disponibilidade de sistema/serviço crítico | >=99,50% | Apurar a disponibilidade do sistema ou serviço durante o período | 1000 pontos a cada 0,1% abaixo da meta | 99,47% | 99,47% | Não Alcançado |
| INMS 1.5 | Disponibilidade de sistema/serviço não-crítico | >=99% | Apurar a disponibilidade do sistema ou serviço durante o período especificado. | 250 pontos a cada 0,1% abaixo da meta | 99,65% | 99,93% | Alcançado |
| INMS 1.14 | Índice de disponibilidade de serviços de infraestrutura | >=99,50% | Apurar a porcentagem de disponibilidade dos serviços de infraestrutura (a) File Server, (b) Telefonia, (c) Mensageria, (d) Servidores de impressão, (e) WI-FI; e (f) Rede. | 250 pontos a cada 0,1% abaixo da meta | 97,50% | 98,35% | Não Alcançado |
| PONTUAÇÃO TOTAL | | | | | | | - |

------------------------------



Além do resumo por órgão, haverá uma tabela detalhada com órgão, sistema ou serviço, criticidade, período previsto, indisponibilidade programada, indisponibilidade não programada, disponibilidade apurada, meta, conformidade e evidência.

### Aba 6: `ATENDIMENTO_N2`



| Item | Indicadores | Meta | Glosa | Aferição da empresa conforme Relatório | Aferição dos fiscais* | Resultado | Pontuação de Penalidade |
|---|---|---|---|---|---|---|---|
| INMS 1.1 | Quantidade de incidentes atendidos dentro do prazo | >= 98% | (Total de incidentes atendidos dentro do prazo / Total de incidentes abertos no período) x 100 | 165 pontos (mensalmente em caso de índice abaixo de 98%) + (20 pontos a cada 0,1% abaixo da meta). | 100% | 100% | Alcançado 0 |
| INMS 1.2 | Quantidade de requisições atendidos dentro do prazo | >= 95% | (Total de requisições atendidas dentro do prazo conforme tipo de prioridade) / Total de requisições abertas no período conforme tipo de prioridade) x 100 | Prioridade Alta: 20 pontos a cada 0,1% abaixo da meta Prioridade Média: 15 pontos a cada 0,1% abaixo da meta Prioridade Baixa: 10 pontos a cada 0,1% abaixo da meta | 100% | 99,56% | Alcançado 0 |
| INMS 1.6 | Eficácia no tratamento de chamados (requisições e incidentes) | >= 97% | Total de chamados atendidos – Total de chamados reabertos) / Total de chamados atendidos | 200 pontos a cada 0,5% abaixo da meta | 99,90% | 99,87% | Alcançado 0 |
| INMS 1.7 | Satisfação dos usuários | >= 80% | (Total de Avaliações Positivas – “Satisfeitos” e “Muito Satisfeitos”) / Quantidade total de avaliações | 250 pontos a cada 1% abaixo da meta | 87,09% | 100% | Alcançado 0 |
| INMS 1.9 | Tempo médio de implementação de uma mudança | ≥90% das mudanças realizadas no prazo acordado | 200 pontos a cada 1% abaixo da meta (ex.: 88%, 2 x 200) | N/A | N/A | Não foram realizadas mudanças no ambiente no período | 0 |
| PONTUAÇÃO TOTAL | | | | | | | 0 |

------------------------------

A ausência de mudança no período será registrada como **Não aplicável no período**, e não como zero, evitando interpretar ausência de demanda como descumprimento.

### Aba 7: `OPERACAO_N3`



| Item | Indicadores | Meta | Glosa | Aferição da empresa conforme Relatório | Aferição dos fiscais* | Resultado | Pontuação de Penalidade |
|---|---|---|---|---|---|---|---|
| INMS 1.1 | Quantidade de incidentes atendidos dentro do prazo | >= 98% | (Total de incidentes atendidos dentro do prazo / Total de incidentes abertos no período) x 100 | 165 pontos (mensalmente em caso de índice abaixo de 98%) + (20 pontos a cada 0,1% abaixo da meta). | 99,55% | 99,62% | Alcançado 0 |
| INMS 1.2 | Quantidade de requisições atendidos dentro do prazo | >= 95% | (Total de requisições atendidas dentro do prazo conforme tipo de prioridade) / Total de requisições abertas no período conforme tipo de prioridade) x 100 | Prioridade Alta: 20 pontos a cada 0,1% abaixo da meta Prioridade Média: 15 pontos a cada 0,1% abaixo da meta Prioridade Baixa: 10 pontos a cada 0,1% abaixo da meta | 98,86% | 98,69% | Alcançado 0 |
| INMS 1.3 | Quantidade de projetos atendidos dentro do prazo | 100% | (Total de dias dos projetos conforme foram definidos) / (Total de dias de projetos conforme foram definitivos + somatórios dos dias de atraso) | 200 pontos a cada 1% abaixo da meta | N/A | N/A | Alcançado 0 |
| INMS 1.6 | Eficácia no tratamento de chamados (requisições e incidentes) | >= 97% | Total de chamados atendidos - Total de chamados reabertos) / Total de chamados atendidos | 200 pontos a cada 0,5% abaixo da meta | 99,71% | 99,68% | Alcançado 0 |
| INMS 1.7 | Satisfação dos usuários | >= 80% | (Total de Avaliações Positivas - "Satisfeitos" e "Muito Satisfeitos") / Quantidade total de avaliações | 250 pontos a cada 1% abaixo da meta | 90% | 100% | Alcançado 0 |
| INMS 1.9 | Tempo médio de implementação de uma mudança | ≥90% das mudanças realizadas no prazo acordado | 200 pontos a cada 1% abaixo da meta (ex.: 88%, 2 x 200). | 100% | 100% | Alcançado 0 | |
| INMS 1.10 | Taxa de implantação de controles de segurança | Será acordado com a CONTRATADA o framework de segurança a ser utilizado ou atividades que deverão ser executadas para implementação de controles de segurança. = 100% | 1000 pontos a cada controle não implementado | 100% | 100% | Alcançado 0 | |
| INMS 1.14 | Índice de disponibilidade de serviços de infraestrutura | >=99,50% | Apurar a porcentagem de disponibilidade dos serviços de infraestrutura (a) File Server, (b) Telefonia, (c) Mensageria, (d) Servidores de impressão, (e) WIFI; e (f) Rede. | 250 pontos a cada 0,1% abaixo da meta | 97,50% | | Não Alcançado |
| PONTUAÇÃO TOTAL | | | | | | | 00,00 |

------------------------------




### Aba 8: `EVIDENCIAS`

Será o registro central dos documentos comprobatórios.

#### Colunas

1. identificador da evidência;
2. competência;
3. órgão;
4. serviço;
5. grupo operacional;
6. indicador;
7. descrição da evidência;
8. sistema de origem;
9. período coberto;
10. número do documento SEI;
11. nome do arquivo;
12. endereço ou caminho do documento;
13. data de emissão;
14. responsável;
15. evidência suficiente?;
16. observação do fiscal.

Uma mesma evidência poderá ser associada a mais de um indicador, mas deverá indicar claramente se se refere ao MinC, ao MTur ou a um ambiente compartilhado.

### Aba 9: `GLOSAS`

Concentrará apenas ocorrências com impacto financeiro.

#### Colunas

1. competência;
2. órgão;
3. item contratual;
4. serviço;
5. indicador;
6. resultado;
7. meta;
8. faixa de descumprimento;
9. percentual de ajuste;
10. valor-base;
11. valor da glosa;
12. reincidência;
13. justificativa;
14. número da ocorrência;
15. decisão do fiscal;
16. observação do gestor.

> **Regra importante:** a fórmula de glosa somente será fechada após a identificação completa da tabela ou metodologia de ajuste do Termo de Referência. O resultado técnico pode ficar abaixo da meta sem que o percentual financeiro seja arbitrado manualmente.

### Aba 10: `PAINEL_GERENCIAL`

Painel visual contendo percentual geral de conformidade, indicadores conformes, não conformes e não aplicáveis, pendências de evidência, glosa total, valor recomendado, comparação MinC versus MTur, distribuição por N1, N2, N3 e NOC/SOC e tendência por competência.
