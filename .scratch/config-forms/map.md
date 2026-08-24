# Config forms roadmap

- **Status:** resolved
- **Type:** wayfinder:map

## Destination

Estender o app Wayfinder (`src/ui`) — que hoje só tem formulário pro
indicador INMS (ver `.scratch/wayfinder-ui/map.md`, resolvido) — com
formulário pras 3 famílias de config restantes que ainda fazem sentido
editar via UI:

1. `categorias.yaml` (per-órgão, mapeamento categoria → INMS → modo de
   filtro).
2. `datasets.yaml` (arquivo único em `_shared`, alias → arquivo CSV +
   opções de parsing).
3. "Contrato" — bundle leve de 3 arquivos globais pequenos:
   `dados_contratuais.yaml` (chave/valor), `ajuste_inms.yaml` e
   `desconto_regulatório.yaml` (formula + descricao).

Inclui redesenhar a navegação da sidebar pra acomodar múltiplas famílias de
formulário (hoje só existe o modo "arquivo raw" + o modo "indicador INMS").

**Fora de escopo:** `anexo_e.yaml` — tabela de referência de ~100 linhas
extraída programaticamente de um HTML do termo de referência (ver
`docs/research/anexo-e-inms-1.8.md`), não um alvo de edição manual; qualquer
coisa já listada como fora de escopo no map anterior (visualização de saída,
apoio a decisão fiscal, CSS de workspace raw, deploy multi-usuário).

## Notes

- Domain: pyauditor (contrato 40/2022 MinC/MTur) — ver `CONTEXT.md` raiz.
  Vocabulário desta chartering session (tier A/B, "contract-constants
  bundle") é jargão de tooling da UI, não pertence ao `CONTEXT.md`.
- Cada ticket **carrega execução** — decide e implementa no mesmo ticket,
  mesmo padrão do map anterior (prototype/decide → build), não é spec-only.
- Fatos já levantados (não precisam de novo research):
  - `configs/_shared/` tem precedência sobre `configs/<orgao>/` sempre que
    existe (`config/resolution.py::resolve_config_dir`) — e existe. Logo
    `configs/{MinC,MTur}/datasets.yaml` são cópias mortas, nunca lidas pelo
    pipeline; só `configs/_shared/datasets.yaml` é usado de fato.
  - `categorias.yaml` **não** tem fallback `_shared` — é genuinely per-órgão
    (`Grupo_executor` difere entre MinC/MTur, ver docstring de
    `config/categorias.py`). Schema: `mode: grupo_executor|whole_indicator`;
    `grupo_executor` exige exatamente um de `in_values` (lista) ou
    `catch_all_contains` (string) — validado em `config/categorias.py`.
  - Sidebar atual (`src/ui/app.js`) só tem dois modos: lista plana de
    arquivo raw, e árvore agrupada por indicador INMS
    (`<details>` por `ind.key` → botão por órgão). Não generaliza pra mais
    de uma família de formulário ainda.
- Ticket de sidebar: chamar Skill `grilling` — decisão de UX compartilhada
  por todas as famílias, vale desenhar antes das outras.
- Ticket de `categorias.yaml`: chamar Skill `prototype` (HITL) antes de
  travar layout, mesmo padrão do ticket 01 do map anterior (branching
  `in_values`/`catch_all_contains` é mais condicional que o form INMS).

## Decisions so far

- **01 — sidebar model:** agrupamento de topo por família (INMS / Categorias
  / Datasets / Contrato / Other files); órgão como sub-nível só onde a
  família tem um (INMS árvore existente, Categorias — dois botões `MinC`/
  `MTur` hardcoded, mesmo padrão do `<select>` de agência do pipeline
  já existente, sem endpoint de descoberta novo). Datasets e Contrato são
  singletons — um botão de nav cada, sem lista. `state.mode` generalizou
  para `file|indicator|categoria|dataset|contrato`; dirty-tracking usa
  `state.formDirty` pra qualquer modo != `file`. Refeito
  `.scratch/wayfinder-ui/issues/01-inms-form.md`'s path-as-dot-string no
  form engine genérico (`renderChildren`/`walkTarget`/etc, `src/ui/app.js`)
  pra path-as-array-de-chaves — chaves de categoria como `"1.1"` têm ponto
  literal e quebravam o split por `.`. Implementado em `server.py` (rotas
  `/api/categoria`, `/api/datasets`, `/api/contrato`) + `app.js`.
- **02 — dead datasets.yaml duplicates:** confirmado (grep + diff bit-a-bit)
  que `configs/{MinC,MTur}/datasets.yaml` eram idênticos a
  `configs/_shared/datasets.yaml` e nunca lidos fora do resolver; nenhum
  teste referenciava os arquivos reais do repo (só fixtures em `tmp_path`).
  Removidos via `git rm`.
- **03 — datasets.yaml form:** endpoint `/api/datasets` (GET/PUT), validado
  por `DatasetEntry` (pydantic, `config/manifest.py`). Layout: card por
  alias (reusa o idioma visual já existente do form INMS) em vez de
  `<table>` literal — evita CSS novo, mesma legibilidade pra ~14 entradas.
  Backend em `src/ui/datasets_form.py`.
- **04 — categorias.yaml form:** endpoint `/api/categoria?orgao=` (GET/PUT),
  validado por `CategoriasFile` (pydantic, `config/categorias.py`). UI por
  entrada INMS: select de `mode` (grupo_executor/whole_indicator) + select
  de "tipo de filtro" (match-any-destes-valores vs. contains-este-texto) que
  troca a forma do campo abaixo — usuário nunca vê os nomes literais
  `in_values`/`catch_all_contains`. **Desvio da decisão original:** o ticket
  pedia rodar a Skill `prototype` (4 variantes, HITL) antes de travar
  layout, mesmo padrão do form INMS. Sessão não-interativa (sem humano pra
  revisar variantes) — decisão de layout tomada direto pelo agente em vez
  disso, registrada aqui para revisão posterior se o layout não agradar.
  Backend em `src/ui/categorias_form.py`.
- **05 — contract-constants bundle:** endpoint único `/api/contrato`
  (GET/PUT) cobrindo os 3 arquivos numa tela só, 3 seções. Nenhum dos 3
  arquivos tem modelo pydantic hoje (`ajuste_inms`/`desconto_regulatório`
  nem são lidos pelo pipeline) — validação própria: mapeamento raso
  string→string, mesma regra que `excel/dados_contratuais.py` já assume.
  `formula` não ganhou tratamento especial (texto simples, como esperado);
  `descricao` renderiza como `<textarea>` em vez de `<input>` de uma linha
  (única exceção no form engine genérico, por nome de chave). Backend em
  `src/ui/contrato_form.py`.

## Not yet specified

<!-- nada além do que já virou ticket; fog desta rodada foi totalmente
     especificada durante o charting -->

## Out of scope

- **`anexo_e.yaml`** — tabela de referência gerada programaticamente a
  partir de `docs/termo_de_referencia/anexo_e_desconformidade_tecnica.html`;
  não é um alvo de "form de edição", e sim (se algum dia precisar mudar) uma
  ferramenta de "regenerar a partir da fonte" — destino diferente.
