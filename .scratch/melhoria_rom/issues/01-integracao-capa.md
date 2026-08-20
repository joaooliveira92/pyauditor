Type: grilling
Status: resolved

## Question

Como o ROM gerado por `measure()` passa a ler dados da capa (`capa_MinC.xlsx` /
`capa_MTur.xlsx`) para preencher Competência, Período inicial/final da
aferição e o rodapé de Responsáveis (Fiscal técnico, Fiscal requisitante,
Fiscal administrativo, Gestor do contrato)?

Pontos a fechar:

- **Camada**: `src/pyauditor/engine/pipeline.py` hoje não depende de
  `openpyxl`/`pyauditor.excel`. `measure()` ganha um parâmetro
  `capa_path: Path | None` e lê `read_capa_fields` internamente, ou o
  `capa_fields: dict` já lido é passado de fora (por `cli/measure.py`, que já
  sabe resolver o caminho da capa por órgão) até `render_rom`, mantendo
  `engine/` livre de dependência de Excel?
- **Resolução do caminho da capa por órgão**: `cli/report.py` já recebe
  `capa_path` explicitamente do chamador (ver `cli/main.py`). `cli/measure.py`
  precisa do mesmo — checar como `main.py` hoje decide entre `capa.xlsx`,
  `capa_MinC.xlsx` e `capa_MTur.xlsx` por órgão/comando, e replicar a mesma
  convenção para `measure`.
- **Comportamento quando a capa não existe ou o campo está vazio** (ex.:
  `bootstrap` não rodou, ou fiscal ainda não preencheu "Fiscal técnico"):
  falha dura, warning + campo em branco no ROM, ou placeholder tipo
  `[a preencher]`? Ver como `run_report` já trata "Valor mensal vigente"
  ausente (`cli/report.py:56-63`) como precedente de estilo.
- **Timing**: a capa pode ser preenchida pelo fiscal *depois* de `measure`
  rodar (ROM já gerado). O ROM deve documentar que os campos de
  identificação/responsáveis refletem o estado da capa **no momento da
  geração**, não um valor imutável — isso deveria virar timestamp/nota no
  template?

## Answer

**Camada**: `engine/pipeline.py` continua sem depender de `openpyxl`. A
leitura da capa acontece em `cli/measure.py`, reaproveitando
`read_capa_fields` (o mesmo padrão que `cli/report.py:56` já usa) — o dict
resultante é passado como parâmetro extra `capa_fields` para
`render_rom(result, capa_fields=...)`, e não como um `capa_path` dentro de
`measure()`.

**`--capa-path` em `measure`**: `measure_parser` (main.py) ganha
`--capa-path` (default `None`), resolvido por órgão via `_capa_path_for`
(main.py:191) — a mesma função já usada por `bootstrap`/`report`, sem
inventar uma segunda convenção. `MeasureRequest` ganha o campo `capa_path`;
`cli_main` calcula `per_orgao_capa` dentro do loop de `_each_single_orgao` e
passa adiante para `run_measure`.

**Capa ausente ou campo vazio**: não fatal. Se `capa_path` não existir, ou um
campo específico (`Fiscal técnico`, `Competência`, `Período inicial/final da
aferição`, `Fiscal requisitante`, `Fiscal administrativo`, `Gestor do
contrato`) vier vazio/ausente do dict de `read_capa_fields`, `cli/measure.py`
emite `logger.warning` uma vez por competência/órgão (não por indicador) e o
ROM renderiza `[a preencher]` nesse campo — mesmo precedente de "Valor
mensal vigente" ausente em `cli/report.py:59-63`.

**Nota de "momento da geração"**: confirmado que o ROM traz uma frase fixa
avisando que os campos vindos da capa (identificação + responsáveis)
refletem o estado da capa **no momento em que o ROM foi gerado**, não um
valor final imutável — texto exato e posição ficam para o ticket "Estrutura
de seções do template" (02), agora desbloqueado.

