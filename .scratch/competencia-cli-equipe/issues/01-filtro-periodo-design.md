---
Type: grilling
Status: resolved
---

# Onde mora o filtro de período e como o YAML o declara

## Question

Desenhar o ponto único de filtragem por período de aferição. split lê os CSVs brutos (categorias), measure lê os CSVs de `_split` e os whole_indicator direto do bruto, sintetico.xlsx relê tudo — onde a função de filtro é chamada para que todos herdem (decisão Q7 do mapa)? Como `source.period_column` é declarado no YAML (obrigatório para indicador filtrável — ausência é erro de configuração, não filtro silencioso) e como o parser lida com os dois formatos existentes (`DD/MM/AAAA HH:MM` nos incidentais vs `YYYY-MM` nas pré-computadas)? Onde vive a derivação canônica competência→(início, fim) — `_mes_bounds` hoje está privada em `excel/capa.py`?

## Answer

Decidido com o humano (2026-08-21):

1. **Lar canônico**: módulo novo `src/pyauditor/periodo.py` com dataclass `PeriodoAfericao(inicio, fim)`, derivação `mes_bounds(competencia)` e a função pura de filtro. `excel/capa.py` deleta sua `_mes_bounds` privada e importa daqui; engine/cli nunca dependem de excel.
2. **Derivação**: período vem exclusivamente da competência posicional obrigatória da CLI (`2026-06` → 01/06/2026 a 30/06/2026). Nada lê capa, nada infere de dados.
3. **Declaração**: coluna em `source.period_column` no YAML do indicador (flui para configs derivadas do split via `model_copy`). Formato da célula inferido entre os dois conhecidos, disjuntos: `DD/MM/AAAA HH:MM` e `YYYY-MM`.
4. **Um cérebro, três chamadas** (precedente `categoria_filter.py`): split filtra antes de separar categorias (row_count/outros refletem o período); measure filtra após `load_rows`, inclusive `_split` CSVs (re-filtrar é idempotente); sintetico filtra após `read_raw_csv`.
5. **Obrigatoriedade na execução**: `period_column` opcional no modelo pydantic; `measure`/`run_split`/sintetico recebem o `PeriodoAfericao` da CLI e, com ele presente (todo fluxo real), Source sem `period_column` = erro acionável apontando o YAML. Testes unitários que chamam `measure()` sem período não são afetados.
6. **Política de linhas**, com flag `--strict` nos entry points que leem dataset:
   - data legível fora da janela: descartada SEMPRE, com contagem;
   - célula vazia/ilegível: com `--strict`, descartada (conta no descarte; se zerar o dataset, WARN); sem o flag (default), segue para os quality gates como hoje;
   - zero linhas dentro da janela: WARN e segue (charting).
7. **Fluxo interativo**: herda — invoca os mesmos comandos e não expõe flags, então roda no default permissivo.

Nesta entrega o `--strict` governa apenas as linhas sem prova de período.
