# 05 — Composição com fog já existente (multi-asset 1.14, ingestão manual 1.8/1.10)

Type: grilling
Status: resolved

Blocked by: 01

## Question

`.scratch/inms-pipeline-fog/issues/01-multi-asset-file-discovery.md` já cobre INMS 1.14 como "múltiplos pares YAML+CSV, um por ativo/serviço". A diretiva do ticket 01 também coloca 1.14 na categoria "Operação e Sustentação" (só uma categoria, sem conflito de N categorias). Mas isso levanta a pergunta geral: quando um INMS tem tanto segmentação por ativo/serviço (multi-asset) quanto por categoria/Grupo_executor, como as duas dimensões compõem — é um produto cartesiano (N ativos × M categorias = N×M medições), ou as dimensões nunca coexistem na prática? E os INMS de entrada manual (1.8/1.10, fog em `.scratch/inms-pipeline-fog/issues/02` e `03`) — a segmentação por categoria se aplica a eles também quando o schema de ingestão manual for definido, ou são estruturalmente incompatíveis com Grupo_executor?

## Answer

Resolvido via grilling (2 rodadas, todas aprovadas) + confronto com a tabela real do Anexo D para o INMS 1.14 (fórmula "para cada um dos serviços (a,b,c,d,e,f)... a meta se refere a cada serviço e não ao somatório").

### 1. Composição multi-asset × categoria: produto cartesiano por ativo

O INMS 1.14 participa de 2 categorias (`MONITORAMENTO_NOC_SOC` e `OPERACAO_N3`, ambas `mode: whole_indicator` — ticket 02) e tem 6 ativos nomeados no Anexo D (File Server, Telefonia, Mensageria, Servidores de impressão, WI-FI, Rede), cada um já uma medição independente por si só (fog `inms-pipeline-fog/issues/01`). A composição é **por ativo**: cada um dos 6 ativos é medido sob cada uma das 2 categorias — **6 × 2 = 12 medições independentes**, cada uma seu próprio ROM. `whole_indicator` aqui significa apenas "sem filtro de Grupo executor" — não colapsa os ativos, que continuam independentes por razão distinta (Anexo D já os define como medições separadas).

Termos formalizados em `CONTEXT.md`: novo termo **Ativo** (serviço de infraestrutura nomeado no Anexo D, dimensão de segmentação distinta de Categoria) e nota de composição adicionada ao termo **Categoria**.

### 2. Layout no xlsx sintético (ticket 04)

A aba do INMS 1.14 no `sintetico.xlsx` mostra as 12 linhas (ativo × categoria), com coluna **"Ativo"** no lugar de "Grupo executor" para este caso, agrupadas e subtotalizadas por categoria (bloco NOC/SOC, depois bloco Operação N3) — extensão mínima do padrão já aprovado no ticket 04 (linhas agrupadas com subtotal), sem inventar uma estrutura de aba nova.

### 3. INMS 1.8/1.10: incompatibilidade estrutural, fechada

Os schemas de ingestão manual de 1.8 (ocorrências Anexo E) e 1.10 (checklist QRC/QCSI) — fog `inms-pipeline-fog/issues/02` e `03` — são registros de ocorrência/checklist, não solicitações de atendimento com "grupo executor". A ausência da coluna é estrutural ao tipo de dado, não uma lacuna de coleta a ser revisitada. **Decisão definitiva**, não entra em "Not yet specified" do mapa.

### 4. Caso geral produto-cartesiano (multi-asset × Grupo_executor real): fora de escopo

Nenhum INMS com Grupo_executor real (1.1/1.2/1.3/1.6/1.7/1.9) é multi-asset hoje, e isso é **estrutural ao Anexo D**, não coincidência: multi-asset cobre indicadores de monitoramento de infraestrutura nomeada (NOC/SOC), enquanto Grupo_executor existe em indicadores de fila de atendimento/chamado — são categorias de indicador diferentes no próprio contrato. O caso geral (produto cartesiano com `split` de fato rodando por ativo) fica **fora de escopo** do mapa — se surgir no futuro, é uma extensão do modelo, a ser tratada como novo esforço, não uma lacuna deste.
