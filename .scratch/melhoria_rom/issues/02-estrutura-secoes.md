Type: grilling
Status: resolved
Blocked by: 01

## Question

Qual é a estrutura final de seções do novo template ROM — ordem, headers
exatos, e quais seções são comuns aos 5 shapes vs específicas?

Usar a seção 6 da auditoria (`.scratch/melhoria_rom/auditoria.md`) como
referência solta, adaptando ao que existe de fato em `MeasurementResult`
após o ticket "Integração com a capa" (Fiscal técnico, Competência,
Período — Aviso: ticket 01) e aos metadados de plumbing já aprovados (hash,
nome do arquivo, delimiter/encoding, timestamp, versão do pipeline/config).

Pontos a fechar:

- Seção "Identificação" (contrato, órgão, competência, período, data de
  processamento, versão do pipeline/config, hash) substitui ou antecede o
  atual cabeçalho `# ROM — <contractual_id> ...`?
- "População" renomeada para "Linhas aprovadas pelo quality gate" (decidido)
  — em que seção entra a ressalva de que isso não é população contratual:
  nota inline, ou um parágrafo dedicado?
- "Ressalva interpretativa" (3 leituras, achado 8) só aparece quando
  `config.penalty is not None` (hoje só o shape `ratio` usa
  `config.penalty` — ver `engine/strategies/ratio.py`) — confirmar que
  `segmented_ratio`/outros shapes nunca precisam dela, e decidir o texto
  fixo de enquadramento quando ela aparece.
- Seção "Resultado vs meta" muda de nome/formato para acomodar
  "Pontuação apurada" no lugar de "Penalidade" — mantém formato atual ou
  vira tabela?
- Rodapé "Responsáveis" — layout (lista vs tabela) e onde entra a nota de
  que reflete o estado da capa no momento da geração (ver ticket 01).
- Confirmar quais headers markdown (`##`, `###`) usar para não quebrar
  parsers/consumidores existentes do ROM (checar se algo além de humano lê
  o markdown — `rom/summary.py` já é o canal estruturado, então o
  markdown em si não deveria precisar ser re-parseado, mas confirmar).

## Answer

Esqueleto aprovado (comum aos 5 shapes), na ordem:

```markdown
# ROM — <contractual_id> [— <asset>] (<name>)

## Identificação
- Contrato / Órgão / Competência / Período da aferição (capa) / Data de
  processamento / Versão do pipeline / Versão da configuração / Arquivo de
  origem (hash SHA-256, delimitador, codificação)

## Linhas aprovadas pelo quality gate
- Linhas lidas / Linhas aprovadas + ressalva de que não equivale à
  população contratual completa

## Rejeições
<tabela atual, inalterada>

## Memória de cálculo
<renderer por shape, inalterado>

## Ressalva interpretativa   ← condicional, ver abaixo
<tabela das 3 leituras (linear adotada / degraus completos / teto)>

## Resultado vs meta
- Meta / Resultado / "Pontuação apurada: N pontos" + nota de rodapé fixa
  (não implica sanção administrativa)

## Responsáveis
- Fiscal técnico / Fiscal requisitante / Fiscal administrativo / Gestor do
  contrato (capa)

---
*Nota fixa: competência, período e responsáveis refletem o estado da capa no
momento em que este ROM foi gerado — não são valores definitivos.*
```

- **Ressalva interpretativa**: só renderiza quando `config.penalty is not None`
  (hoje só shape `ratio`) **e** `calculation.penalty_points > 0` — indicadores
  conformes não mostram a seção (as 3 leituras dariam o mesmo resultado
  trivial). Conteúdo exato da tabela e onde a matemática das 3 leituras é
  calculada ficam para o ticket "Apresentação da ressalva interpretativa" (04).
- **"Critério contratual"** (item 2 do modelo da seção 6 da auditoria —
  população/numerador/meta/fonte no Anexo D) fica **fora** deste mapa: exigiria
  um campo novo de citação textual por indicador no YAML, que não está entre
  os metadados "baratos" já aprovados — é conteúdo redacional por indicador,
  não estrutura de relatório. Movido para "Not yet specified" como algo que um
  esforço futuro (que já mexe em regra de negócio/config) pode cobrir.
- **Headers**: tudo em `##`, nenhum `###` — inclusive a tabela da ressalva
  interpretativa, sem subheader dedicado. Consistente com o template atual.

