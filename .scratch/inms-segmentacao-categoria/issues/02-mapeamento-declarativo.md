# 02 — Schema e arquivo do mapeamento declarativo categoria→Grupo_executor→INMS

Type: grilling
Status: resolved

Blocked by: 01

## Question

O ticket 01 decidiu que o mapeamento categoria→`Grupo_executor`→INMS mora num arquivo declarativo separado (ex.: `categorias.yaml`), consumido pela etapa `split`. Falta decidir: nome e localização do arquivo (ao lado dos `inms-<n>.yaml`? em `config/`?), schema exato (chaves, como representar o catch-all "contém (CIT), exceto os grupos X/Y" de forma declarativa e não hardcoded, como representar `outros`, e como representar a variante "indicador inteiro, sem `Grupo_executor`" usada por `MONITORAMENTO_NOC_SOC` — ver ticket 01, item 11 — sem forçar um filtro vazio artificial), e se é um arquivo único para todos os INMS ou um por INMS. Popular o arquivo com a diretiva completa do ticket 01 (itens 9 e 11) faz parte da resolução.

## Answer

Resolvido via grilling (2 rodadas de perguntas fechadas + achados factuais sobre dados reais de `input/MinC/2026/06/` e `input/MTur/2026/06/`, este segundo atualizado pelo usuário no meio da sessão). **Esta resolução substitui a diretiva do ticket 01 item 9 quanto à lista concreta INMS↔categoria** — a semântica geral do ticket 01 (papel de filtro pré-engine, N categorias = N medições, `outros` contábil) continua valendo inalterada.

### 1. Arquivo e localização

Um arquivo central por órgão, ao lado do manifesto já existente `configs/<orgao>/datasets.yaml` (mesmo precedente): **`configs/<orgao>/categorias.yaml`** — `configs/MinC/categorias.yaml` e `configs/MTur/categorias.yaml`. Não é um arquivo global nem um por INMS: os valores literais de `Grupo_executor` diferem por órgão (achado factual — ver seção 4), então um arquivo por órgão é obrigatório, não só estilístico.

### 2. Orientação e schema

Chaves de topo por **categoria** (espelha a estrutura em que a diretiva do usuário foi dada; a etapa `split`, ticket 03, deriva a visão por-INMS programaticamente). Schema unificado com um campo discriminador `mode` por entrada INMS-dentro-de-categoria:

```yaml
categorias:
  ATENDIMENTO_N1:
    label: "Atendimento Remoto aos Usuários"
    inms:
      "1.1": {mode: grupo_executor, in_values: ["(CIT/MINC) - 1º Nível"]}
      "1.2": {mode: grupo_executor, in_values: ["(CIT/MINC) - 1º Nível"]}
      "1.7": {mode: grupo_executor, in_values: ["(CIT/MINC) - 1º Nível"]}
      "1.11": {mode: whole_indicator}
      "1.12": {mode: whole_indicator}
      "1.13": {mode: whole_indicator}
  ATENDIMENTO_N2:
    label: "Atendimento Presencial aos Usuários"
    inms:
      "1.1": {mode: grupo_executor, in_values: ["(CIT/MINC) - 2º Nível", "(CIT/MINC) - 2º Nível/RJ", "(CIT/MINC) - 2º Nível/BDB"]}
      "1.2": {mode: grupo_executor, in_values: [...]}
      "1.7": {mode: grupo_executor, in_values: [...]}
  OPERACAO_N3:
    label: "Operação e Sustentação da Infraestrutura de TI"
    inms:
      "1.1": {mode: grupo_executor, catch_all_contains: "(CIT)"}
      "1.2": {mode: grupo_executor, catch_all_contains: "(CIT)"}
      "1.3": {mode: grupo_executor, catch_all_contains: "(CIT)"}
      "1.7": {mode: grupo_executor, catch_all_contains: "(CIT)"}
      "1.6": {mode: whole_indicator}
      "1.9": {mode: whole_indicator}
      "1.14": {mode: whole_indicator}
  MONITORAMENTO_NOC_SOC:
    label: "Monitoramento de Ambiente (NOC/SOC)"
    inms:
      "1.4": {mode: whole_indicator}
      "1.5": {mode: whole_indicator}
      "1.14": {mode: whole_indicator}
```

(`configs/MTur/categorias.yaml` segue o mesmo schema, com `in_values`/`catch_all_contains` usando os literais do MTur — ver seção 4 — e **1.6 em modo `grupo_executor`** em vez de `whole_indicator`, único ponto em que MinC e MTur divergem estruturalmente.)

- **Modo `grupo_executor` com lista explícita** (`in_values`): reaproveita o tipo `ColumnIn` já existente no engine (`src/pyauditor/config/models.py`), usado hoje em `SegmentedCategory`.
- **Modo `grupo_executor` com catch-all** (`catch_all_contains`): não é um filtro fechado — a exclusão (grupos já cobertos pelas outras categorias daquele INMS/órgão) é **computada em tempo de execução** pela etapa `split`, não duplicada/hardcoded no YAML. Evita a lista de exclusão ficar dessincronizada quando outra categoria muda.
- **Modo `whole_indicator`**: sem filtro nenhum — o dataset inteiro do INMS naquela competência conta como a categoria, sem passar pela etapa `split`. Usado tanto para o caso original (`MONITORAMENTO_NOC_SOC`, dataset pré-agregado sem a coluna) quanto para o caso novo descoberto nesta sessão (INMS que deveriam ter `Grupo_executor` mas cujo CSV real não tem).
- **`outros`**: continua implícito/automático — qualquer linha não capturada por nenhuma categoria declarada daquele INMS (substantiva ou catch-all) cai em `outros` automaticamente; não tem entrada no YAML.
- **INMS sem categoria** (1.8, 1.10): ausência de qualquer entrada no arquivo — não precisa de marcação negativa explícita.
- Chaves de categoria = as máquina já fixadas no ticket 01 item 8, mais `label:` com o nome humano. Nova categoria adicionada nesta sessão: `"Monitoramento de Ambiente (NOC/SOC)"` é o label humano oficial de `MONITORAMENTO_NOC_SOC` (a diretiva completa do usuário nesta sessão nomeou a categoria pela primeira vez; ticket 01 só tinha a chave-máquina).

### 3. Diretiva completa e final (substitui ticket 01 item 9)

Fornecida pelo usuário nesta sessão, cobrindo as 4 categorias substantivas + NOC/SOC de forma explícita e completa (sem a linha malformada do ticket 01):

- **Atendimento Remoto aos Usuários**: 1.1, 1.2, 1.6, 1.7, 1.11, 1.12, 1.13
- **Atendimento Presencial aos Usuários**: 1.1, 1.2, 1.6, 1.7, 1.9
- **Operação e Sustentação da Infraestrutura de TI**: 1.1, 1.2, 1.3, 1.6, 1.7, 1.9, **1.14**
- **Monitoramento de Ambiente (NOC/SOC)**: 1.4, 1.5, 1.14

**1.14 pertence às duas últimas categorias simultaneamente — confirmado intencional pelo usuário** (não é resíduo da correção do ticket 01 item 12): gera duas medições independentes, mesmo resultado bruto do indicador (pré-agregado, sem `Grupo_executor`) rotulado sob as duas.

### 4. Achados factuais que motivaram o modo `whole_indicator` além do NOC/SOC

Verificação real contra `input/MinC/2026/06/*.csv` e `input/MTur/2026/06/*.csv` (este último atualizado pelo usuário no meio da sessão):

| INMS | MinC tem `Grupo_executor`? | MTur tem `Grupo_executor`? |
|---|---|---|
| 1.1, 1.2, 1.7 | Sim — `(CIT/MINC) - 1º/2º Nível[/RJ\|/BDB]` + catch-all `(CIT) <grupo>` | Sim — `CIT - 1º/2º Nível[/Anexo]` + catch-all `(CIT) <grupo>` / `CIT - <grupo>` |
| 1.3 | Sim (coluna presente), mas **0 linhas no período** (não ativado) | Sim (coluna presente), mas **0 linhas no período** (não ativado) |
| 1.6 | **Não** — dataset é uma tabela SLA já agregada (`Acordo de Nível de Serviço;No Prazo;%;...`), sem `Grupo_executor` | Sim — mesmo catálogo de 1.2/1.7 (dado real, chegou durante esta sessão) |
| 1.9 | **Não** — tabela pré-agregada de mudanças (`competencia;ambiente_id;...;trmp_requisicoes_atendidas_no_prazo;...`) | **Não** — mesma estrutura pré-agregada |
| 1.11, 1.12 | **Não** — logs brutos de telefonia (`Data e Hora Início,ORIGINADOR,...`), sem conceito de grupo executor | **Não** — mesma estrutura |
| 1.13 | **Não** — tabela trimestral pré-agregada (`competencia;trimestre;...;inms_1_13_percentual;...`) | **Não** — mesma estrutura |
| 1.4, 1.5, 1.14 | **Não** (inalterado do ticket 01) | **Não** (inalterado do ticket 01) |

Decisão do usuário sobre como resolver cada caso "sem coluna":
- **INMS pertencente a uma única categoria** (1.11, 1.12, 1.13 → só Atendimento Remoto): `whole_indicator`, resultado inteiro rotulado com essa categoria — implicitamente equivalente a "todo o indicador é N1".
- **INMS pertencente a múltiplas categorias, sem coluna em nenhum órgão** (1.9 → Presencial + Operação; 1.6 no MinC → Remoto + Presencial + Operação): a decisão do usuário foi **não duplicar** — o indicador inteiro conta só como **OPERACAO_N3** (a categoria de infraestrutura), saindo das demais. Regra aplicada a 1.9 (ambos os órgãos) e a 1.6 exclusivamente no MinC (no MTur, 1.6 tem a coluna real e participa normalmente das 3 categorias via filtro).
- **Exceção explícita a essa regra de não-duplicação**: 1.14, que o usuário confirmou como intencionalmente duplicado entre `MONITORAMENTO_NOC_SOC` e `OPERACAO_N3` (seção 3).

### 5. Fora do escopo desta resolução

O mecanismo de revisão periódica da lista (o que fazer quando novos dados reais chegarem e os literais de `Grupo_executor` mudarem de novo, como aconteceu com o MTur nesta própria sessão) não foi definido — seguirá em "Not yet specified" no mapa.
