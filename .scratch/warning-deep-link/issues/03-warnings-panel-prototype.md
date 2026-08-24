# Warnings panel: layout + scroll-to-and-highlight (prototype first)

- **Status:** resolved
- **Type:** wayfinder:prototype
- **Blocked by:** 01, 02

## Question

Hoje não existe nenhuma exibição de warnings na UI (`app.js`/`index.html`
não têm nenhuma menção a "warning"). Decisões do charting já travadas (não
re-abrir): painel novo, estreito (só a lista de warnings, não um resumo
completo da run); warnings sem `target` resolvível (ver ticket 01)
renderizam como texto plano, sem link forçado; clicar num warning com
`target` resolvido deve navegar (reusando o `guardDiscard()` já existente
pra descartar mudanças não salvas) até o formulário certo e **rolar +
destacar** o card aninhado exato — não só abrir o formulário certo e deixar
o usuário procurar; painel some inteiro (não aparece vazio) quando o job
rodado não é `run`.

O que falta decidir aqui é layout e mecânica concretos: onde o painel de
warnings vive na tela (perto do `<pre id="output">` existente? dentro do
`<aside class="pipeline">`? uma seção nova?); como o "rolar até" navega
entre árvores diferentes (ex.: um `target` de categoria pode estar numa
categoria/órgão que não é a atualmente aberta — precisa expandir o
`<details>` certo na sidebar antes de abrir o form); como o destaque visual
se parece e por quanto tempo dura; se um clique num warning cujo form já
está aberto (mesma categoria/órgão) ainda dispara scroll+highlight ou é
no-op.

Construir um protótipo (chamar Skill `prototype`) reagindo a uma proposta
concreta — mesmo padrão do form INMS (`.scratch/wayfinder-ui/issues/01-inms-form.md`)
e do form de categorias (`.scratch/config-forms/issues/04-categorias-form.md`).

Carrega execução: após a decisão de layout, implementar o painel real
(consome `warnings`/`target` do ticket 02, navega + destaca usando os
`data-path` já existentes no form engine genérico de `app.js`).

## Answer

Protótipo com três variantes construído (`prototype` skill, sub-shape A —
adaptação da página real, gated por `?warnings=1&variant=A|B|C`, dados
mock realistas contra as `categorias.yaml` reais de MinC/MTur): A (lista
inline no painel de pipeline, sob o `<pre id="output">`), B (card
flutuante dismissível, canto inferior direito), C (badges na sidebar +
lista inline expansível por grupo). João reagiu ao vivo e escolheu **B**.

Protótipo completo (as três variantes + switcher de dev) capturado no
branch throwaway `prototype/warning-deep-link-panel` (commit `e57a97f`),
fora da `main` — não fica em `app.js`.

Implementado de verdade em `excel-requisicoes`:

- `index.html`: `<div id="warnings-panel">` fixo, fora do grid layout
  (`position: fixed`, canto inferior direito).
- `app.js`: `renderWarningsPanel(warnings)` — chamado a cada `poll()` com
  `data.warnings` (já vem `[]` de jobs não-`run`, então o painel some
  sozinho sem lógica extra de "isso foi `run`?"); e no início de
  `startJob()` com `[]` pra limpar o painel da run anterior e resetar
  `state.warningsDismissed`. Cada warning sem `target` renderiza como
  `<div>` inerte; com `target`, como `<button>` que chama
  `openWarningTarget()`: `guardDiscard()` → `openCategoria(target.orgao)`
  → `highlightTargetField(target.path)`, que acha o campo via
  `findFieldByPath` (compara `JSON.stringify` do `data-path` parseado,
  não a string bruta escapada), abre todo `<details>` ancestral, dá
  `scrollIntoView` e pulsa `.warning-highlight` por ~1.9s. Botão "×"
  marca `state.warningsDismissed = true` até a próxima run.
- `styles.css`: estilos permanentes do card (`.warnings-panel`,
  `.warning-row` etc.) e da animação de destaque
  (`.warning-highlight`/`@keyframes warnPulse`); removido o CSS marcado
  como protótipo.
- Só `family: "categorias"` tem navegação implementada hoje —
  `openWarningTarget` ignora silenciosamente qualquer outra família (não
  existe ainda; nenhum código migrado além dos dois do ticket 01).

Testado: `node --check app.js` limpo; suite completa
(`uv run pytest`) — 637 passed, as 2 falhas em
`tests/test_excel_sintetico.py` são de um trabalho concorrente
não-relacionado (`_render.py`/`_types.py`, branch `excel-requisicoes`,
confirmado intocado por este ticket). `ruff check` em `server.py` só
mostra dívida pré-existente (mesmo padrão documentado nos tickets 01/02).
Verificado manualmente contra o servidor real (`src/ui/server.py
--workspace .`) com avisos mock apontando pros `categorias.yaml` reais de
MinC e MTur.
