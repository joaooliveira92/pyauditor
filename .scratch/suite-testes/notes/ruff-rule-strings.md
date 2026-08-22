# Pesquisa — Regra do Ruff como gate para o padrão "duas strings coladas" (concat implícita)

**Data:** 2026-08-22
**Escopo:** decisão do ticket 02 do wayfinder (suite-testes). Nada foi resolvido nem fechado.
**Método:** leitura das docs oficiais (docs.astral.sh/ruff) + verificação empírica local com Ruff 0.16.3 (via `uv run ruff`) em diretório temporário fora do repo. Não houve contato com git/GitHub.

---

## 1. A regra: família `ISC` (flake8-implicit-str-concat)

Fonte: <https://docs.astral.sh/ruff/rules/#flake8-implicit-str-concat-isc>

| Código | Nome | Estável desde | Fix | Padrão | Detecta |
|---|---|---|---|---|---|
| `ISC001` | `single-line-implicit-string-concatenation` | v0.0.201 | 🛠️ "Combine string literals" | não | concat implícita de literais numa só linha — `'a' 'b'` |
| `ISC002` | `multi-line-implicit-string-concatenation` | v0.0.201 | — | não | concat implícita multi-linha; por default **só via backslash**; com `allow-multiline = false`, qualquer multi-linha |
| `ISC003` | `explicit-string-concatenation` | v0.0.201 | 🛠️ "Remove redundant '+' operator" | não | concatenação explícita com `+` — `'a' + 'b'` |
| `ISC004` | `implicit-string-concatenation-in-collection-literal` | desde 0.16.0 | 🛠️ (marcado *unsafe*) | ✅ default | concat implícita dentro de list/tuple/set literal |

Nenhuma dessas regras está atrás de `preview`. O índice de regras não marca nenhuma ISC com 🧪 ("All rules not marked as preview, deprecated or removed are stable"). A legenda e o status de cada ISC estão em <https://docs.astral.sh/ruff/rules/>.

- Detalhe ISC001: <https://docs.astral.sh/ruff/rules/single-line-implicit-string-concatenation/>
- Detalhe ISC002: <https://docs.astral.sh/ruff/rules/multi-line-implicit-string-concatenation/>
- Detalhe ISC003: <https://docs.astral.sh/ruff/rules/explicit-string-concatenation/>
- Detalhe ISC004: <https://docs.astral.sh/ruff/rules/implicit-string-concatenation-in-collection-literal/>

**Versão mínima para o pyauditor:** ISC001/002/003 existem desde v0.0.201 (2023) — compatíveis com o `ruff>=0.12` do repo. `ISC004` exige Ruff 0.16+ e já vem ligada por default (não faz mal mantê-la; ela é ortogonal — pega o caso de **comma faltando** em coleções, não o padrão de costura em texto).

## 2. Cobertura do caso "sem espaço intencional entre literais"

A família `ISC` flag **a sintaxe de concatenação**, não o conteúdo:
- `ISC001` pega `'inteiro ASCII' 'positivo, '` e `'header do' 'CSV — …'` (adjacência numa linha, com ou sem espaço real dentro dos literais — pois Python concatena byte a byte; **nunca** insere espaço).
- `ISC003` pega o mesmo texto escrito com `+`.
- `ISC002` + `allow-multiline = false` pega a forma repartida em duas linhas dentro de parênteses (o padrão exato reportado na regressão do repo: ~443 costuras em 53 arquivos).

Não há opção do tipo "exigir separação" (espaço). As únicas alavancas são:
- `lint.flake8-implicit-str-concat.allow-multiline` (default `true`) — Fonte: <https://docs.astral.sh/ruff/settings/#lint_flake8-implicit-str-concat_allow-multiline>.
  - `true` (default): multi-linha implícita *entre parênteses* é permitida; só backslash é proibido.
  - `false`: proíbe a multi-linha implícita **inteira**; e **auto-desabilita o `ISC003`** (explícito `+`) porque "de outra forma seria impossível escrever um multi-linha que satisfaz o linter" (docs ISC003).
- Casos legítimos: não há distinção automática. Quem precisa de adjacência real (ex. compor `'Nº'` + `'Solicitação'` a partir de coluna) deve marcar `# noqa: ISC001` na linha, ou prever `per-file-ignores` por padrão de arquivo (ex.: testes que montam literais longos). Ver seção 4.

Verificação empírica (Ruff 0.16.3):
- `x = 'inteiro ASCII' 'positivo, '` → `ISC001 [*]`.
- `x = 'a' + 'b'` → ISC003 só flag quando `allow-multiline = true` (com `false`, a regra sai do ar — confirmado: `explicit.py` deixou de ser sinalizado).
- `( 'a' \n 'b' )` (parênteses, multi-linha) → **não** flag por default; flag com `allow-multiline = false` (confirmado em `long_implicit.py`: ISC002).

---

## 3. Interação com o formatter — comportamento de `ruff format` e `--check`

Fontes: <https://docs.astral.sh/ruff/formatter/> (seção "Conflicting lint rules") e <https://docs.astral.sh/ruff/rules/multi-line-implicit-string-concatenation/> (seção "Formatter compatibility").

Evidência **decisiva para o gate**, medida localmente com Ruff 0.16.3:

| Entrada | `ruff format` faz | `ruff format --check` |
|---|---|---|
| `x = ('a' \n 'b')` (cabe na linha) | **une os dois literais num só** — `x = 'ab'` — a quebra de linha some | "Would reformat: …" **exit 1** |
| `x = 'a' \n 'b'` via backslash | funde os dois em `'ab'` (uma linha) | exit 1 |
| `x = 'a' \n 'b'` cujo texto estoura line-length | mantém a multi-linha implícita (parênteses) — imutável | exit 0 (já formatado) e depois `ruff check` **flag ISC002** se `allow-multiline=false` |
| `x = 'a' + 'b'` | não mexe (operador `+` explícito preservado) | exit 0 |

Ou seja: **o formatter VOMITA dois literais adjacentes num único literal** quando o resultado cabe nos 80 cols — ele **remove** a quebra de linha e apaga a "costura". Consequência dupla para o gate:

- Positiva: costuras pequenas (que cabem numa linha) tendem a ser **fundidas** pelo próprio `ruff format`, e o pool de "costura visível" fica autoilimitado.
- Negativa/perversa: uma vez fundida num único literal, o texto **sem o espaço** foi "eternizado" — e o linter ISC fica cego (não há mais concat). O ISC protege o **momento da escrita com dois literais**: quem introduzir `'...ASCII'` + `'positivo, '` como dois literais (numa ou em duas linhas) sem o espaço, será sinalizado antes do format fundir.

Os docs confirmam que o formatter "can introduce new multi-line implicitly concatenated strings" e a recomendação oficial (página do ISC002) é: habilitar `ISC001` junto, de modo a desmotivar toda a concat implícita — ou manter `allow-multiline = true`. Quando se trava ISC002 + `allow-multiline = false`, o format e o linter podem "brigar": o format mantém a multi-linha (é a forma canônica dele) e o `check` a sinaliza. No teste local, `ruff format` não alterou o arquivo multi-linha (exit 0) e o lint sinalizou ISC002 — os dois gates não se conflitam, mas todo multi-linha implícito passa a ser erro no lint.

---

## 3B. Confirmações empíricas avulsas

- Fix do ISC001 com `--fix`: `x = 'inteiro ASCII' 'positivo, '` vira literal único `x = 'inteiro ASCIIpositivo, '` — **concatenação byte a byte**, preserva o "erro" (ok, o fix não adivinha espaço).
- ISC001/ISC002 não estão em `select` default (`F`, `E`, `B`, `UP`, `RUF` etc. — veja <https://docs.astral.sh/ruff/rules/>), por isso precisam ser adicionados ao `extend-select`.
- O repo pyauditor já roda com `preview = true`; nenhuma ISC precisa de preview — não há impacto de toggle de preview para isto.

---

## 4. Configuração mínima recomendada para o pyauditor

Arquivo: `pyproject.toml`, seção `[tool.ruff.lint]` existente.

Passo A — ligar o gatilho (opção estrita, cobre o padrão real do repo — duas linhas entre parênteses):

```toml
[tool.ruff.lint]
# ... (mantenha o select atual E isso:)
extend-select = ["ISC001", "ISC002", "ISC003"]

[tool.ruff.lint.flake8-implicit-str-concat]
allow-multiline = false
```

Efeito colateral documentado: com `allow-multiline = false`, o `ISC003` (concatenação explícita `+`) é **auto-desabilitado** (docs ISC003 + confirmação empírica). O custo: escrever `'a' + 'b'` deixa de ser sinalizado. Compromisso:
- Se você quer pegar também o `+` (o "com ou sem operador" da pergunta), use **`extend-select = ["ISC001","ISC002","ISC003"]` e NÃO mexa no `allow-multiline`** (default `true`). Nesse modo, a concat multi-linha entre parênteses **não** é pega — o padrão da regressão volta a escapar.
- O pyauditor: a regressão real foi multi-linha/com parênteses. **Decisão sugerida: ir com a opção estrita (`allow-multiline = false`)** + `ISC001`/`ISC002` obrigatórios; se o + for prioridade, alterna para o pacote inclusivo acima. Escolher um dos dois: não dá para ter `ISC003` ativo E `allow-multiline = false`.

Perfil `per-file-ignores` (tests — adicionar apenas se necessário):
```toml
[tool.ruff.lint.per-file-ignores]
# (junto dos ignores existentes) — ex.: se testes montam strings concatenadas de propósito:
"tests/**/*.py" = ["ISC001"]
```

Caso legítimo ("strings que DEVEM ficar junto em runtime", ex.: compor título a partir de coluna): o linter ISC não distingue intenção; para um caso pontual e intencional, aceite `# noqa: ISC001` inline (ou `# noqa: ISC002`) — os docs mostram que o linter ignora linhas com `# noqa`. Para casos estruturais, refatore para f-string ou `"".join([...])`, eliminando a costura na origem.

Limpeza do legado: para o gate funcionar sem dor, o estado atual (~443 costuras) precisa ser corrigido/resolvido ANTES de ligar ISC002 estrito — senão o `ruff check` do CI explode no diff inteiro. Isso é o trabalho do ticket de correção das 53 arquivos; o gate entra depois da correção e passa a vigia o futuro.

---

## 5. Regra do Ruff vs driver AST custom via pytest — recomendação

Fontes: <https://docs.astral.sh/ruff/rules/> (primeira-party, mais de 900 regras) e <https://docs.astral.sh/ruff/formatter/> (integração lint+format no mesmo binário).

| Critério | Regra ISC do Ruff | Driver custom (pytest + `ast`) |
|---|---|---|
| Detecção do padrão | ISC001/002/003: sintaxe de concat, sem semântica de "espaço" | pode ir ALÉM: inspecionar o texto concatenado real (ex.: exigir que a costura comece/termine com espaço em branco). É a única vantagem real do custom |
| Fix | ⬅ ISC001 tem autofix (`ruff check --fix`) | nenhum — só sinaliza |
| Infra | zero: roda no gate `ruff check` existente; zero infra nova | novo plugin, novo trecho de ast.walk, manutenção do conjunto de testes |
| Formatter | integrado de verdade: docs do formatter listam ISC002 como regra com "formatter compatibility" — o próprio Ruff resolve a tensão | o driver custom NÃO sabe o que o `ruff format` fará com o arquivo (e o format **funde** os literais!) — o checker custom passaria a inspecionar um AST que o format já reescreveu; visão em stale |
| Velocidade | em Rust, com cache | rodado via pytest (interpretado em Python) |

Conclusão para o ticket 02: **use a regra `ISC` do Ruff como gate**, sem driver custom. Motivos (docs + empírico):
1. os gates do repo já rodam `ruff check` e `ruff format` no CI — a regra encaixa sem nova infra (docs: linter e formatter são unificados no mesmo CLI).
2. ISC001 tem autofix e interage com `--fix` no mesmo fluxo;
3. o formatter, ao fundir literais que cabem, reduz o pool de costuras visíveis — sobra o caso estrito (multi-linha com `allow-multiline=false`) que a regra cobre.
4. o driver custom só valeria a pena se o requisito **semântico** (espaço de escrita na costura) fosse inegociável — mas `ruff format` reescreve o arquivo entre leituras e o driver ficaria vendo texto já fundido, sem vantagem sobre o lint.
5. Se um dia quiser a inspeção de "espaço na costura", o caminho barato é solicitar uma micro-regra nova ao upstream do Ruff, não um driver via pytest.

O `ISC` cobre o "escritor" — que é onde a costura vira bug; o espaço intencional de escrita já é responsabilidade do autor, e a regra força a decisão explícita (noqa ou escrita correta) em cada costura nova.

---

## Recomendação (executiva)

1. **Regra:** família `ISC` (flake8-implicit-str-concat). Nome estável, nenhuma atrás de preview. Versão mínima: v0.0.201 para ISC001/002/003 (ok com ruff>=0.12 do repo); `ISC004` é extra desde 0.16 (default ligado).
2. **Cobre "sem espaço"?** Sim, sintaticamente: `ISC001` (uma linha), `ISC003` (com `+`) e `ISC002`+`allow-multiline=false` (duas linhas entre parênteses). Não há opção "exigir separação" — legítimos via `# noqa`/per-file. O espaço nunca é inferido; a regra apenas força o autor a decidir.
3. **Formatter:** hoje `ruff format` **funde** literais adjacentes quando o texto cabe no `line-length` (apaga a quebra de linha); `ruff format --check` desses casos sai 1 ("Would reformat"). Em texto mais longo (estoura 80), a multi-linha implícita é preservada e a regra ISC002 (estrita) sinaliza no `ruff check`.
4. **Snippet recomendado:**
   ```toml
   [tool.ruff.lint]
   extend-select = ["ISC001", "ISC002", "ISC003"]
   [tool.ruff.lint.flake8-implicit-str-concat]
   allow-multiline = false
   ```
   (default: sem `allow-multiline=false`, troque para o pacote alternativo descrito na seção 4 — perde a captura da multi-linha.)
5. **Fator formatter é decisivo e resolve a favor da regra:** o `ruff format` funde os literais que cabem na linha, escondendo a maior parte das costuras — mas lint e format rodam sobre o mesmo AST; passar para um driver custom via pytest seria re-inventar o que Ruff já provê (fix, cache, `--fix`, line-length/default) para ganhar apenas a inspeção de "espaço de escrita", que trivialmente pode ir como pedido de micro-regra ao upstream.

### Fontes
- Índice de regras e legenda (estabilidade): <https://docs.astral.sh/ruff/rules/>
- ISC001: <https://docs.astral.sh/ruff/rules/single-line-implicit-string-concatenation/>
- ISC002 (e "Formatter compatibility"): <https://docs.astral.sh/ruff/rules/multi-line-implicit-string-concatenation/>
- ISC003: <https://docs.astral.sh/ruff/rules/explicit-string-concatenation/>
- ISC004: <https://docs.astral.sh/ruff/rules/implicit-string-concatenation-in-collection-literal/>
- `allow-multiline` (seção settings): <https://docs.astral.sh/ruff/settings/#lint_flake8-implicit-str-concat_allow-multiline>
- Formatter (exit codes, "Conflicting lint rules", Black compatibility): <https://docs.astral.sh/ruff/formatter/>

Detalhes empíricos nas seções 2/3/5: verificados com `ruff 0.16.3` (via `uv run ruff`) em /var/folders/.../opencode/ruff-isc-test (fora do repo).