# Nota SRP — pacote `rom` (ticket 07)

Data: 2026-08-22 · Escopo: `src/pyauditor/rom/` (`render.py` 352 linhas,
`summary.py` 137, `loading.py` 52, `dedup.py` 40, `__init__.py` vazio).

## Métricas e limitações

- Ferramentas executadas: `ruff` (lint), `mypy` (strict), `pytest` + cobertura
  das suítes `tests/test_rom_render.py`, `test_rom_render_escaping.py`,
  `test_rom_summary.py` e das suítes consumidoras (`test_cli_report`,
  `test_excel_report`, `test_excel_consolidate`, `test_glosas`,
  `test_cli_consolidate`, `test_multi_asset_discovery`).
  **Limitação registrada:** `radon`/`xenon` não estão instalados — complexidade
  ciclomática obtida por análise própria da AST (McCabe simplificado:
  `If`/`For`/`While`/`ExceptHandler` + operandos de `BoolOp`). Valor
  aproximado; serve de sinal, não de métrica de ferramenta.
- `mypy` strict: limpo (0 issues) nos 4 módulos + 3 suítes de teste.
- `ruff`: 75× `E501` (linhas >80) + 2× `S101` (`assert` em produção) em
  `render.py:169` e `summary.py:56`; tudo pré-existente, não usado como
  evidência de SRP, citado apenas como higiene.
- `pytest`: **127 testes** das suítes ligadas ao pacote passando
  (`-o addopts="" --no-cov`; suíte completa segue verde conforme map.md).
- Cobertura observada por módulo (suítes do ticket + consumidores):
  - `render.py` 92–94% (`test_rom_render*`);
  - `summary.py` 86–96%;
  - `loading.py` 84–89% (linhas descobertas 23, 30, 35-36: ramos de erro);
  - `dedup.py` 100% (via `test_glosas`/`test_excel_*`/`test_cli_consolidate`).
- Linhas **físicas** = `wc -l`; linhas **lógicas** ≈ contagem de nós `ast.stmt`.

## Resumo dos candidatos

| Arquivo | Prioridade | Linhas físicas/lógicas | Cobertura (suítes do pacote) | Confiança |
|---|---|---|---|---|
| `rom/render.py` | **MÉDIA** | 352 / 121 stmts | 94% | alta |
| `rom/summary.py` | **BAIXA** | 137 / 74 stmts | 96% | alta |
| `rom/loading.py` | **BAIXA** | 52 / 31 stmts | 84–89% | média |
| `rom/dedup.py` | NÃO RECOMENDADA | 40 / 16 stmts | 100% | alta |
| `rom/__init__.py` | NÃO RECOMENDADA (observar) | 0 | — | média |

Nenhum arquivo atinge a faixa >500 linhas do spec; o maior (`render.py`, 352)
passa dos 300 que pedem "observar", mas coesão alta e complexidade baixa — a
prioridade vem de um achado qualitativo (domínio de cálculo embutido na
apresentação), não da contagem de linhas.

---

## 1. `render.py` — **MÉDIA** (achado principal do pacote)

### Fatos observados

- Camada **de apresentação** com vazamento pontual de **domínio**:
  `_render_ressalva_interpretativa` `render.py:161-194` **recalcula** as três
  leituras da penalidade (linear contínua, degraus completos, "qualquer fração
  inicia novo degrau") em vez de apenas formatar um valor já computado. Usa
  `shortfall` importado da engine (`render.py:18`), `math.floor/ceil`
  (`render.py:178-179`; o `import math` da linha 10 é consumido **somente**
  aqui) e a regra `base + passos × pontos_degrau` (`render.py:174-179`). É
  regra contratual (a "Ressalva interpretativa" do CONTEXT.md:41) vivendo na
  camada de Markdown.
- Dois motivos independentes de mudança recaindo no mesmo arquivo: a
  **metodologia de leitura** da penalidade (novo degrau/arredondamento) e o
  **layout** do Markdown.
- `_org_body` `render.py:243-291` (35 linhas, cc=2) é o orquestrador das seções
  fixas (Identificação, Linhas aprovadas, Rejeições, Memória, Ressalva,
  Resultado vs meta, Responsáveis, rodapé). Coeso — um único motivo (montar o
  corpo do ROM).
- Despacho de memória: `_MEMORIA_RENDERERS` `render.py:106-112`, com 5 renderers,
  cada um uma função de 4–15 linhas, cc 1 — padrão de despacho correto. Em
  `render.py:267`, `_MEMORIA_RENDERERS[config.calculation.shape]` faz `KeyError`
  cru para shape desconhecido (falha de robustez, não de SRP).
- Duplicação pequena da montagem do título entre `render_rom`
  (`render.py:306-308`) e `render_combined_rom` (`render.py:340-342`):
  `format_inms_code` + sufixo de `asset`.
- **O pacote não lê a fonte** — a hipótese do ticket ("um `rom` que lê da fonte
  e renderiza") é refutada como fato: `render.py` recebe o `MeasurementResult`
  já processado (`engine/pipeline.py:measure`); quem lê CSV é a engine
  (`measurement_source`/`categoria_filter`). A única leitura do pacote é de
  sidecar `.json` gerado (em `loading.py`), consumida por `report`/`consolidate`
  — não pela renderização.

### Sinais quantitativos

- 352 linhas físicas / 121 stmts; cc do módulo ≈15; maior corpo `_org_body`
  35 linhas; `_render_ressalva_interpretativa` 29 linhas.
- Cobertura 94% (suíte `test_rom_render*`); ramos abertos `render.py:74, 92,
  231, 342`.

### Hipótese (declarada)

- Que a derivação das leituras linear/degraus da ressalva é **regra de negócio
  da engine** (compõe o entendimento do `penalty`), reaproveitável por qualquer
  consumidor futuro (ex.: `excel/` declarando a ressalva em célula), e não um
  detalhe de formatação.

### Motivos independentes para mudança

1. metodologia/pontuação da ressalva (leitura linear vs degraus) → toca
   `render.py:167-187`;
2. layout do ROM (cabeçalhos, ordem de seções, rodapé) → toca o
   arquivo inteiro;
3. contrato de `IndicatorConfig`/`MeasurementResult`/`Provenance` → toca
   `_render_identificacao` `render.py:124-148`.

### Plano sugerido

1. **Antes**: manter verde `tests/test_rom_render.py`
   (`test_ressalva_interpretativa_shown_with_correct_readings:197`,
   `test_ressalva_interpretativa_omitted_when_conforms:212`,
   `test_ressalva_interpretativa_omitted_when_shape_has_no_penalty:223`), que
   fixam as 3 leituras exibidas. Adicionar teste unitário puro da função
   extraída (entrada → readings) sem passar por Markdown.
2. **Extrair o cálculo**: novo símbolo na engine — `engine/strategies/_target.py`
   (já tem `shortfall`) ou novo `engine/strategies/penalty.py` —
   `penalty_interpretation(config, calculation) -> PenaltyReadings | None`,
   com `PenaltyReadings` dataclass frozen (`linear/floor/ceil` pontos). O
   `render.py` passa a **formatar** o resultado; o `import math` sai do render.
3. **Corrigir o `KeyError`** `render.py:267`: `_MEMORIA_RENDERERS.get(shape)`
   + `ValueError` acionável (mesma disciplina de `_require_list`
   `render.py:25-28`).
4. **Deduplicar o título**: helper `_rom_title(config)` usado por `render_rom` e
   `render_combined_rom`.
5. **API preservada**: `render_rom`, `render_combined_rom` e os 5
   `render_*_memoria` públicos seguem exportados com as mesmas assinaturas (sem
   consumidor externo de `_render_ressalva_interpretativa` — manter um wrapper
   privado apenas para não quebrar o call-site interno `render.py:278`).
6. **Ordem segura**: 1 → 2 (extração mecânica, saída idêntica) → 3/4 → rodar
   suítes do pacote + consumidores + ruff + mypy.

### Risco/benefício

- Risco baixo-médio: o ROM é um artefato com valor fiscal e os 14 testes de
  `test_rom_render*` asseram trechos verbatim — rede de segurança boa.
- Benefício: separa "interpretar o cálculo" (domínio) de "imprimir MD"
  (apresentação); o render perde `math`+`shortfall` embutidos; consumidores
  futuros da ressalva ganham a mesma fonte única.

---

## 2. `summary.py` — **BAIXA**

### Fatos observados

- Módulo coeso e pequeno: `IndicatorSummary` (dataclass `summary.py:25-68`) como
  **DTO serializável** + validação de fronteira no `__post_init__`
  (`summary.py:53-65`), com `to_dict()` para o sidecar `.json`; decisão
  documentada no docstring (`summary.py:26-30`: rejeitar sidecar corrompido no
  load, não no meio da aritmética do Excel).
- `summarize` `summary.py:99-124` aplana o `MeasurementResult` em shape-agnostic;
  o pool de numerador/denominador **delega a `SHAPE_REGISTRY`** já existente na
  engine (`summary.py:127-137`; `base.py:22-29` define o contrato) — fonte
  única, sem segundo despacho por shape.
- Higiene: `assert name in known_fields` em produção (`summary.py:56`, `S101`)
  e `import math` dentro do corpo de `_require_numeric` (`summary.py:80`) em vez
  de topo. A validação usa helpers `_require_*` pequenos (3–10 linhas).
- Sem God object; sem segundo motivo claro de mudança no mesmo arquivo.

### Sinais quantitativos

- 137 linhas físicas / 74 stmts; cc do módulo 15 (puxado por `__post_init__`
  cc 5 e `_require_numeric` cc 5 — validação linear, não acoplamento de
  negócio); 1 classe, 7 funções.
- Cobertura 96% (mypy strict limpo).

### Plano sugerido

1. Não dividir o arquivo. Higiene opcional: mover `import math` para o topo
   (`summary.py:80`) e trocar o `assert known_fields` por `if`+raise
   (`summary.py:56`).
2. **Antes**: nenhum teste novo obrigatório — existem
   `test_rom_summary.py:34-71` (tipos) e `test_indicator_summary_round_trips_through_to_dict`.
3. **Depois**: re-rodar `test_rom_summary.py`; consumidores em `excel/`
   (`inms_base.py:19`, `orgao_consolidation.py:32`, `consolidate.py:51-53`) não
   mudam.

### Risco/benefício

Risco baixo, benefício marginal (higiene). O valor do arquivo é o contrato já
bem desenhado e o pool delegado — não mexer além do necessário.

---

## 3. `loading.py` — **BAIXA**

### Fatos observados

- 52 linhas, 2 funções coesas de leitura de artefatos: `load_summaries`
  `loading.py:16-37` (lê `.json` + cross-check do `orgao` do sidecar contra o
  diretório de origem, com `ValueError` contextual) e `read_valor_base`
  (ausência de `objetos.csv` → warning; malformado → erro; decisão explicitada
  no docstring `loading.py:40-43`).
- I/O + validação na borda: `load_summaries` tem cc 6 (condições de
  cross-check + wrap de exceções com `raise ... from exc` preservando causa —
  correto).
- **Dependência cruzada a observar**: `loading.py:10-11` importa
  `excel/objetos.py` (`OBJETOS_FILENAME`, `read_objetos`) — leitura de "objeto
  contratual" que vive no módulo de Excel embora seu núcleo seja parse de CSV de
  contrato (`excel/objetos.py:1-28`). Não é violação de SRP do `loading`; é uma
  direção de dependência a vigiar (rom → excel) para a síntese.
- Importante: `load_summaries` consome `IndicatorSummary` (o contrato do
  sidecar) mas não usa `render`. loading/dedup existem para os **relatórios**;
  `render` nunca lê disco — `cli/measure.py:275-288` apenas **escreve**
  `render_rom`/`summarize`.

### Sinais quantitativos

- 52 físicas/31 lógicos; cc módulo 8; `load_summaries` 21 linhas cc 6.
- Cobertura 84–89% (linhas descobertas 23, 30, 35-36).

### Plano sugerido

- NÃO criar módulo novo. Melhora cirúrgica opcional: extrair
  `_expected_orgao(roms_dir) -> str | None` (`loading.py:21-23`) como função
  interna pura para reduzir o cc de `load_summaries`.

### Risco/benefício

Baixo; o maior valor seria relocalizar a leitura do `objetos.csv` da camada
`excel` para um ponto neutro de input — decisão do ticket do pacote excel, não
deste.

---

## 4. `dedup.py` — **NÃO RECOMENDADA**

### Fatos observados

- 16 statements; `is_categoria_derived` (4 linhas) e `deduplicate_summaries`
  (11 linhas). Uma responsabilidade única: merge de grupos
  `(contractual_id, asset)` excluindo a base quando há categorías derivadas.
  Docstring registra o bug histórico (`dedup.py:8-13`): um `_is_derived` antigo
  testava `"." in indicator_id` — sempre verdade para códigos INMS (`"1.7"`
  já tem ponto), então nunca excluía a base; a correção é o prefixo
  `f"{contractual_id}."` (`dedup.py:25`).
- Consumidor compartilhado: `excel/report.py:51-52` (glosa) e
  `excel/consolidate.py:52-53` (aba GLOSAS) — a fatoração eliminou cópias
  divergentes (ticket 07).
- Não há segundo motivo para mudar. Cobertura 100%.

### Plano

Nenhum. Falso-positivo: pequeno, coeso e reutilizado — o anti-exemplo de
fragmentação. Registrado para o ticket 08 como módulo saudável.

---

## 5. `__init__.py` — observabilidade de API (observe, NÃO dividir)

- Vazio. Todos os consumidores importam via caminho completo
  `pyauditor.rom.<submod>`, confirmado em 20 referências:
  - `render_*`: `cli/measure.py:57` e 9 suítes de teste;
  - `summarize`/`IndicatorSummary`: `cli/measure.py:58`, `excel/*.py` (4
    arquivos), `test_rom_summary`, `test_multi_asset_discovery`, etc.;
  - `loading`: `cli/report.py:28`, `cli/consolidate.py:29`;
  - `dedup`: `excel/report.py:51-52`, `excel/consolidate.py:52-53`.
- A ausência de `__all__`/re-exports torna a API pública **implícita** — não é
  violação de SRP. Se o pacote crescer, adotar `__all__` explícito; não fazer
  agora (engenharia especulativa).

---

## 6. Achado principal — apresentação × domínio, e a hipótese do ticket

A hipótese do ticket ("um `rom` que lê da fonte **e** renderiza — acúmulo")
**não procede como acúmulo de I/O lendo fonte + render** no mesmo arquivo:

- a separação física em 4 módulos já existe;
- a leitura de **fonte** (CSV de dados) mora na engine (`pipeline.py` /
  `measurement_source`), não em `rom`;
- `loading.py` lê *sidecar JSON* (artefato), não a fonte.

Os dois fatos que redefinem o marco:

1. **O único vazamento real de domínio→apresentação** é
   `_render_ressalva_interpretativa` (`render.py:161-193`): o render **calcula**
   a leitura da penalidade em vez de só formatá-la. É o candidato com maior
   retorno — prioridade MÉDIA do pacote.
2. **O pacote `rom` acumula duas missões distintas** (não duas fontes): servir o
   **pipeline de medição** (`render`/`summary` → artefatos do ROM) e servir o
   **pipeline de relatório/consolidação** (`loading`/`dedup` → sidecars →
   Excel). É um "hub de artefatos" com alto coesão por contrato (`IndicatorSummary`
   como cola), não um God-file; dividir `loading`/`dedup` seria fragmentação. A
   síntese (ticket 08) pode registrar como **coesão de interface válida**.

## 7. Ordem segura de execução (agregada)

1. Reforçar testes da ressalva (unitários puros da extração na engine) —
   manter `test_rom_render*.py` verbatim verde.
2. Extrair `penalty_interpretation` na engine (mecânica, saída idêntica);
   `render.py` passa a formatar (sem mudança de saída do ROM).
3. Corrigir `KeyError` de shape desconhecido (`render.py:267`).
4. Deduplicar título (`_rom_title`). Re-lint/format.
5. Higiene de `summary.py` (remove assert; topo; import math no topo).

## 8. Validações recomendadas

- `mypy src/pyauditor/rom` + os 3 arquivos de teste → já limpo.
- `ruff check src/pyauditor/rom` — esperado os 75×E501/2×S101 pré-existentes;
  após os passos 1–5, `E501` deve cair.
- `pytest <suítes do ticket> -o addopts=""` → 127 testes da amostra; suíte
  completa + gate de cobertura 85% (`pyproject.toml`) ao final.
- Amostra executada nesta nota: `pytest` pacote-rom+consumers → 127 passed.