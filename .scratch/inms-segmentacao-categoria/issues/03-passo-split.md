# 03 — Semântica do passo `split`

Type: grilling
Status: resolved

Blocked by: 01

## Question

O ticket 01 decidiu que a filtragem categoria×`Grupo_executor` vira uma etapa explícita e nova no CLI (tipo `pyauditor split`) que materializa CSVs filtrados em disco antes do `measure`, que continua inalterado. Falta decidir: nome exato do comando, convenção de nomeação/localização dos CSVs filtrados em disco (ex.: `input/<orgao>/<competência>/<inms>/<categoria>.csv`?), o que acontece com a categoria `outros` (é escrita em disco também, só pra auditoria, ou só contada em log/relatório?), idempotência (rerodar `split` sobre o mesmo CSV bruto deve sobrescrever ou falhar se já existir?), e como o `measure` existente descobre qual CSV filtrado usar para qual categoria. Nota: o ticket 02 generalizou o modo "indicador inteiro" (`mode: whole_indicator` em `categorias.yaml`) para além do `MONITORAMENTO_NOC_SOC` original — cobre também 1.11/1.12/1.13 (única categoria, sem `Grupo_executor`) e, por decisão do usuário, 1.9 e 1.6-no-MinC (múltiplas categorias nominais, sem coluna em nenhum órgão → contam só como `OPERACAO_N3`) e 1.14 (duplicado entre `MONITORAMENTO_NOC_SOC` e `OPERACAO_N3`, caso intencional). `split` não se aplica a nenhum INMS em modo `whole_indicator`; confirmar que o `measure` sabe pular a etapa pra todos eles, não só pro trio original 1.4/1.5/1.14, e como o `catch_all_contains` (grupos não cobertos pelas outras categorias do mesmo INMS/órgão) é resolvido em tempo de execução — ver ticket 02 para o schema completo.

## Answer

Resolvido via grilling (2 rodadas de perguntas fechadas, todas aprovadas em bloco). Grounding: código real de `discover_config_files` (glob não-recursivo `config_dir.glob("*.yaml")`, pula arquivos sem chave `indicator`), `Source` (aceita `dataset` via manifesto OU `csv` direto, nunca os dois), e `.gitignore` (`input/` e `/roms/` já ignorados; `configs/` é versionado).

### 1. Mecanismo — `measure` permanece 100% inalterado

`split` gera, por par (INMS, categoria) em `mode: grupo_executor`, dois artefatos:
- **CSV filtrado**: `input/<orgao>/<ano>/<mes>/_split/<inms>/<categoria>.csv`.
- **Config de indicador derivada**: `configs/<orgao>/inms-<n>.<categoria>.yaml` — copia `quality_gates`/`calculation`/`target`/`penalty` do `inms-<n>.yaml` base, muda só `id` e `source.csv` (aponta pro CSV filtrado). Usa **`source.csv` direto, nunca `source.dataset`** — `split` não toca em `datasets.yaml`.

Convenção de nome reservado (`inms-<n>.<categoria>.yaml`, com ponto extra que o arquivo base nunca tem) deixa a config derivada gitignored (`configs/*/inms-*.*.yaml`) e ainda assim descoberta automaticamente pelo glob não-recursivo já existente de `measure` — nenhuma mudança em `measure` é necessária. Ver ADR [0002](../../../docs/adr/0002-config-por-categoria-gerada-pelo-split.md) para o porquê de gerar em vez de escrever à mão.

### 2. Idempotência

`split` sempre sobrescreve ao rerodar — nunca falha por já existir. Os artefatos são inteiramente derivados e regeneráveis a qualquer momento a partir do CSV bruto + `categorias.yaml`; o bruto original nunca é tocado.

### 3. `catch_all_contains`

Resolvido em tempo de `split` (não de `measure`): lê os valores literais de `Grupo_executor` realmente presentes no CSV bruto daquela competência/órgão, subtrai os já reivindicados por `in_values` de outras categorias do mesmo INMS/órgão em `categorias.yaml`, e o resto vira o filtro efetivo gravado ao escrever o CSV da categoria catch-all.

### 4. Categoria `outros`

`split` escreve só o CSV bruto filtrado (`outros.csv`, auditoria/depuração) — **sem** config de indicador derivada correspondente, já que `outros` é contábil e não entra no cálculo (ticket 01). A contagem de linhas cai no log do `split` (apresentação exata fica pro ticket 04).

### 5. Nome do comando e posição em `run`

`pyauditor split <competência>` — quinto comando standalone, mesmo padrão de `measure`/`bootstrap`/`report`/`consolidate`. Em `run`, entra **entre `bootstrap` e `measure`**, transacional por órgão como os demais (uma falha em `split` de um órgão bloqueia só o `measure` daquele órgão).

### 6. `whole_indicator` pula `split` inteiramente

Confirmado: nenhum INMS em `mode: whole_indicator` passa por `split` — nem CSV filtrado, nem config derivada. Isso cobre o trio NOC/SOC original (1.4/1.5/1.14) **e também** 1.11/1.12/1.13, 1.9, e 1.6-no-MinC (generalização do ticket 02). Pra esses, "a medição da categoria" é a medição do `inms-<n>.yaml` base direto, sem artefato intermediário.

### 7. CONTEXT.md

Nenhum termo novo — as decisões deste ticket são mecanismo de pipeline (nome de comando, convenção de arquivo, estratégia de geração), não vocabulário de domínio; mesma razão pela qual `measure`/`report`/`bootstrap` também não constam do glossário. O conceito de domínio ("cada Categoria gera uma medição independente") já estava coberto pela entrada Categoria existente.
