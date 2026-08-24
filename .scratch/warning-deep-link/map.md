# Warning deep-linking roadmap

- **Status:** resolved
- **Type:** wayfinder:map

## Destination

Um warning do pipeline que aponta pra `categorias.yaml` (hoje os dois
códigos estruturados `in_values_unmatched` e `outros_leftover`, mais
códigos no futuro) pode ser clicado no Wayfinder (`src/ui`) e leva direto
pro campo exato que causou o aviso — não só o arquivo certo, o card aninhado
certo, rolado até a view e destacado.

Isso fecha o item de fog "Deep-linking exato" do
`.scratch/wayfinder-ui/map.md` (Wayfinder UI roadmap), que ficou em aberto
porque dependia do formulário INMS real e da estrutura de warnings
existirem primeiro — ambos já resolvidos.

**Fora de escopo:** estender `--output json`/`summary_json()` pros comandos
por etapa (`bootstrap`/`measure`/`split`/`report`/`consolidate`) — só `run`
tem esse resumo hoje, e estender isso é uma mudança de CLI própria, maior
que uma decisão de deep-linking; migrar mais avisos `unstructured` pra
códigos estruturados além dos dois que já existem — o mecanismo já é
validado por esses dois (um aponta um campo editável específico, o outro um
bucket contábil não-editável), forçar uma terceira migração agora seria
escopo além do destino.

## Notes

- Domain: pyauditor (contrato 40/2022 MinC/MTur) — ver `CONTEXT.md` raiz.
  "Categoria outros" já é termo canônico do glossário (bucket contábil,
  não é entrada editável de `categorias.yaml`) — nenhum termo novo de
  domínio de negócio surge deste esforço; vocabulário de tooling (warning
  acionável, target, deep-link) não pertence ao `CONTEXT.md`, mesmo
  julgamento já registrado no `wayfinder-ui`/`config-forms`.
- Cada ticket **carrega execução** — decide e implementa no mesmo ticket,
  mesmo padrão dos dois maps anteriores (`wayfinder-ui`, `config-forms`).
- Fatos já levantados (não precisam de novo research):
  - Só dois `code` estruturados existem hoje: `in_values_unmatched` e
    `outros_leftover` (`src/pyauditor/categoria_filter.py`), ambos sobre
    `categorias.yaml`. Tudo mais no pipeline ainda reporta
    `code="unstructured"`.
  - `summary_json()['warnings']` (`orchestration/summary_json.py`) já expõe
    a lista estruturada — mas **nada na UI a consome hoje**: `src/ui/app.js`
    e `index.html` não têm nenhuma menção a "warning"; `src/ui/server.py`
    só captura stdout cru do subprocess do pipeline como texto.
  - `--output json` (`render_summary`) só existe pro comando `run`
    (`cli/parser.py`), e só troca o **bloco final** de resumo — logging de
    progresso vai pra stderr, independente do formato do resumo
    (`logging.py`: "logs são escritos em stderr... o resumo de conclusão é
    escrito independentemente em stdout"). `server.py` já funde stderr em
    stdout (`stderr=subprocess.STDOUT`) — trocar pra `--output json` nos
    jobs de `run` não quebra o streaming ao vivo, só troca o painel Rich
    final por uma linha JSON.
  - Ticket de layout do painel de warnings + mecânica de scroll/highlight:
    chamar Skill `prototype` (HITL) — é decisão de "como deve parecer/se
    comportar", mesmo padrão dos formulários do `config-forms`.

## Decisions so far

<!-- one line per closed ticket -->

- [Warning target schema + code-to-target builders](issues/01-warning-target-schema.md) — `WarningTarget`/`WarningTargetJson` (`family`, `orgao`, `path`) adicionado a `Warning`/`WarningJson`; `unmatched_in_values_warnings` resolve o alvo, `outros_warning` fica `None`.
- [Wire summary_json() warnings through server.py for run jobs](issues/02-server-warnings-wiring.md) — `run` ganha `--output json` no `build_command`; `Job.warnings()` parseia a última linha de output como o resumo JSON e `GET /api/pipeline/<id>` expõe `warnings` (`[]` quando não é `run`/não é JSON).
- [Warnings panel: layout + scroll-to-and-highlight (prototype first)](issues/03-warnings-panel-prototype.md) — protótipo de 3 variantes (A: lista inline no painel de pipeline; B: card flutuante dismissível; C: badges na sidebar); João escolheu **B**, implementado em `index.html`/`app.js`/`styles.css`; variantes completas capturadas no branch throwaway `prototype/warning-deep-link-panel`.

## Not yet specified

<!-- nada além do que já virou ticket; a única fog real (estender
     --output json pros comandos por etapa) foi classificada como fora de
     escopo, não fog, porque redefiniria o destino em vez de caminhar até
     ele -->

## Out of scope

- **`--output json` pros comandos por etapa** — só `run` tem resumo
  estruturado hoje; estender isso é mudança de CLI própria, não uma decisão
  de deep-linking. Se algum dia acontecer, os warnings desses comandos
  passam a valer automaticamente pelo mesmo mecanismo — sem precisar
  revisitar este map.
- **Migrar mais códigos `unstructured`** — os dois códigos existentes já
  validam o mecanismo (campo editável específico vs. bucket não-editável);
  cada call site futuro migra quando alguém mexer nele, não como trabalho
  deste map.
