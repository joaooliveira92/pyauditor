# 04 — Setup do Tailwind (standalone CLI, sem npm)

- **Type:** task
- **Status:** resolved
- **Blocked by:** —

## Question

Decidido: Tailwind via **standalone CLI** (binário compilado, sem Node/npm),
gerando um `styles.css` estático versionado — mantém a filosofia
"dependency-free em runtime" do `README.md` atual.

Falta especificar a mecânica: onde o binário standalone fica (baixado
manualmente pelo dev, não commitado; ou um script `scripts/build-css.sh`?),
o arquivo de entrada Tailwind (`tailwind.config` mínimo, ou `@import
"tailwindcss"` direto se usando a v4 do CLI), como o output compilado
substitui `src/ui/styles.css` hoje, e a paleta/tokens que precisam replicar o
visual atual (dark/light via `color-scheme: dark light`, cores de `.primary`/
`.danger`/`.badge` etc. em `styles.css`).

Task AFK: o agente pode baixar o standalone CLI, gerar a config mínima, e
compilar um primeiro `styles.css` a partir das classes atuais do
`index.html`, documentando o comando de rebuild no `README.md`.

## Answer

Mecânica: `scripts/build-css.sh` baixa o binário standalone (pinado em
`v4.3.3`) pra `.tailwindcss-cli/` (gitignored, não commitado) na primeira
execução, detectando plataforma (macOS/Linux, arm64/x64), e compila
`src/input.css` → `styles.css` (`--minify`), que continua commitado.

Sem `tailwind.config` — CLI v4 usa CSS-first config. `src/input.css` importa
só `tailwindcss/utilities` (não `tailwindcss` inteiro, pra não puxar o
preflight/reset que colidiria com o CSS já existente) com `source(none)` +
`@source "../*.html"` explícito, pra restringir o scan de candidatos a
`index.html` só — sem isso o CLI varre todo arquivo do diretório (README,
app.js, server.py) e captura palavras soltas como nomes de utility class
(`.relative` apareceu do texto solto até eu restringir a fonte).

Paleta/tokens atuais: preservados **verbatim** dentro de `src/input.css`
(cores, `--panel`/`--line`/`--accent`/`--danger`, `color-scheme` via
`<meta>` em `index.html`) — nenhuma classe utility é usada em `index.html`
hoje, então o layer de utilities compila vazio e o resultado visual do
`styles.css` gerado é idêntico ao anterior (`git diff` confirma: só
reformatação/minificação, mesmas regras). O toolchain fica pronto pra
formulários futuros adotarem utility classes incrementalmente sem precisar
reescrever o CSS hoje.

README documenta o comando de rebuild (`./scripts/build-css.sh`).
