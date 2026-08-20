Label: wayfinder:map

# Melhoria do ROM Markdown (3/10 → especificação para reescrita)

## Destination

Uma especificação suficiente para reescrever `src/pyauditor/rom/render.py` (+ os
campos de apoio em `pyauditor/rom/summary.py`, `pyauditor/engine/pipeline.py`,
`pyauditor/cli/measure.py`) de modo que o ROM markdown pare de mentir por
omissão sobre suas próprias limitações — usando `.scratch/melhoria_rom/auditoria.md`
como referência de achados, mas **sem** corrigir a regra de negócio subjacente
(ver `docs/adr/0001-rom-report-declara-limitacoes-em-vez-de-corrigir-regra.md`).
Fim do mapa = tickets resolvidos = pronto para implementar.

## Notes

- Domínio: `CONTEXT.md` (termos: ROM, Pontuação apurada, Ressalva interpretativa,
  Linhas aprovadas pelo quality gate) e `docs/adr/0001-...md`.
- Skills a consultar ao resolver tickets: `grilling`, `domain-modeling`,
  `research` (quando a pergunta for sobre comportamento do `openpyxl`/instalação
  do pacote).
- Referência primária dos achados: `.scratch/melhoria_rom/auditoria.md`.
- Template atual documentado em `portal/reference/rom.md` (desatualizado assim
  que a reescrita acontecer — ver "Not yet specified").

## Decisões já fechadas em conversa (não viraram ticket — fixam o destino)

- **Escopo**: template + metadados baratos (hash do CSV, nome do arquivo,
  delimiter/encoding, timestamp de processamento, versão do pipeline, versão
  da config) + leitura da capa (`read_capa_fields`) para Competência, Período
  inicial/final da aferição e Responsáveis. Regra de negócio (achados 1, 3,
  6-completo, validação formal do achado 8) fica para um esforço separado.
- **Modelo da seção 6 da auditoria**: referência, não alvo literal — adaptado
  por shape.
- **Todos os 5 shapes** (`ratio`, `segmented_ratio`, `count_difference`,
  `external_catalog_sum`, `precomputed_table`) ganham o esqueleto comum
  (identificação, ressalvas, responsáveis); reconciliação/classificação
  detalhada só faria sentido para `ratio`/`segmented_ratio` mas fica fora
  (depende de dado de pipeline não coberto aqui).
- **Nota "3/10"**: autoavaliação informal, sem prazo/processo formal amarrado.
- **Seções 8-9 da auditoria** (encaminhamento, contraditório, assinatura
  digital, segregação de funções, amostragem documental, desenho de testes de
  aceitação — achado 10) fora de escopo: julgamento humano/processo
  organizacional, não saída de script.
- **Terminologia**: "Penalidade" → "Pontuação apurada" + nota de rodapé fixa
  (consistente com `CONTEXT.md`, que já evita "penalidade" para Glosa).
- **"Linhas aceitas"** → "Linhas aprovadas pelo quality gate" + ressalva de
  que isso não é população contratual.
- **Ressalva interpretativa (achado 8)**: calcular e mostrar as 3 leituras
  (linear/degraus completos/teto) como aritmética de transparência — sem o
  script decidir qual vale contratualmente.
- **Responsáveis**: vêm de `read_capa_fields(capa_path)` (`Fiscal técnico`,
  `Fiscal requisitante`, `Fiscal administrativo`, `Gestor do contrato`), não
  de campos vazios estáticos.

## Decisions so far

- [Versão do pipeline/config](issues/03-versao-pipeline-config.md) — `importlib.metadata.version("pyauditor")` funciona hoje (0.1.0, editable install via `uv sync`), fallback `git rev-parse --short HEAD` → `"dev"`; hash da config = SHA-256 sobre o `raw_text` já lido em `load_config`/`discover_configs` (precisa guardá-lo numa variável e propagar `config_path`/hash até `render_rom`, que hoje não tem acesso a isso).
- [Integração com a capa](issues/01-integracao-capa.md) — leitura fica em `cli/measure.py` (não em `engine/`), reaproveitando `read_capa_fields`/`_capa_path_for`; `measure` ganha `--capa-path`; capa/campo ausente é não fatal (`logger.warning` + `[a preencher]` no ROM); ROM traz nota fixa de que os campos da capa refletem o estado no momento da geração.
- [Estrutura de seções do template](issues/02-estrutura-secoes.md) — esqueleto final (Identificação, Linhas aprovadas pelo quality gate, Rejeições, Memória de cálculo, Ressalva interpretativa condicional, Resultado vs meta, Responsáveis, nota de rodapé); "Ressalva interpretativa" só quando `config.penalty is not None` e `penalty_points > 0`; "Critério contratual" (citação do Anexo D) fica fora — moveu para "Not yet specified".
- [Apresentação da ressalva interpretativa](issues/04-apresentacao-ressalva-interpretativa.md) — cálculo das 3 leituras vive em `rom/render.py` (reusa `shortfall` de `_target.py`, motor de cálculo não muda); tabela com linear marcada "(adotada)"; separador decimal fica em ponto, consistente com o resto do template.

## Not yet specified

- Texto/copy exato de cada rótulo trocado (fino demais para ticket agora —
  sai natural da implementação, uma vez a estrutura de seções decidida).
- Estratégia de teste automatizado do novo template (quantos golden files,
  snapshot por shape) — estrutura final de seções já fechada (ticket 02),
  falta só desenhar a suíte.
- Atualização de `portal/reference/rom.md` e `docs/spec/inms-pipeline.md`
  para refletir o novo formato — puramente mecânica agora que o esqueleto
  do ticket 02 está fechado.
- Se/como estender a evidência de parsing do achado 7 além de
  delimiter/encoding (já aprovado) — verificação mais profunda de
  contaminação HTML fica em aberto para o esforço de pipeline.
- "Critério contratual" (citação textual do Anexo D/Tabela por indicador,
  item 2 do modelo da auditoria) — exige campo novo de config por indicador;
  fora deste mapa, candidato a esforço futuro que já mexe em regra de negócio.

## Out of scope

- Achados 1, 3, 6 (reconciliação/classificação completa da população,
  recálculo independente de "No prazo") — regra de negócio, não renderização.
- Achado 8, validação formal da interpretação linear (submissão à gestão
  contratual/jurídica) — organizacional, não automatizável.
- Achado 10 (desenho dos testes de aceitação) — não é sobre geração de ROM.
- Seções 8-9 da auditoria (contraditório, assinatura digital, segregação de
  funções, amostragem documental) — julgamento humano/processo, fora do
  alcance de um script Python.
