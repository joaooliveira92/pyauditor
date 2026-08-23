# 01 — Rede de testes diretos da lógica de categorias

**What to build:** testes unitários puros (sem tocar em CSV nem em CLI) para as funções de resolução de categorias que hoje só são cobertas indiretamente via integração (`pyauditor split`/`measure`): a resolução de valores por categoria (com a exclusão de valores já reivindicados por `in_values` de `catch_all_contains`), o erro de sobreposição de categorias, o residual "outros", os avisos de `in_values` sem correspondência no CSV e a conversão de chave INMS para nome-base de config. Trata-se de travar o comportamento atual antes de qualquer refactor que toque essas funções — é a rede de segurança que destrava os tickets 04 e 05 e reduz o diagnóstico difuso de bugs de categoria.

**Blocked by:** nenhum — pode começar imediatamente.

**Status:** resolved

- [x] Cada função-alvo tem teste unitário direto chamando o símbolo de produção (sem passar por CLI/workbook).
- [x] Casos de negócio cobertos: valor de `in_values` excluído de `catch_all_contains`; sobreposição entre categorias → `ValueError` com mensagem acionável; residual `outros`; aviso para categoria sem correspondência no CSV; base config da chave `1.<n>`.
- [x] O comportamento atual é documentado nos testes como valores determinísticos (não "golden" opaco).
- [x] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes; cobertura não cai abaixo do gate.

## Contexto (do relatório de fricção)

As funções de categoria são as mais propensas a bug (overlap, `catch_all_contains`, warnings) e hoje só são exercitadas por testes de integração (`test_cli_split`/`test_cli_measure`), o que torna o diagnóstico difuso. Diferenciado de `read_raw_csv`, que já tem teste próprio.

## Answer

Criado `tests/test_categoria_filter.py` (22 testes) cobrindo as quatro funções-alvo como testes puros, chamando os símbolos de produção de `pyauditor.categoria_filter` sem passar por CLI/workbook:

- `compute_categoria_values`: `in_values` com correspondência exata; exclusão de `in_values` de `catch_all_contains` (vale para todo o INMS, em qualquer ordem: o `catch_all` desiste do valor de `in_values` mesmo quando vem antes na lista); substring literal com `)` fechando (não casa `(CIT/MINC)`); `in_values` reivindicando literais independentemente dos valores reais; residual `outros`; erro de sobreposição em duas variantes: mesmo literal `in_values` em duas categorias ("aparece em mais de uma categoria") e dois `catch_all` que casam o mesmo valor real ("sobrepõe valores já reivindicados"). A segunda sobreposição é o único caso que a exclusão de `in_values` não absorve; in_values×catch_all nunca gera o erro, o valor é silenciosamente preemptado.
- `unmatched_in_values_warnings`: sem aviso quando tudo casa; aviso com "possível typo/renomeação, categoria ficará sem linhas" quando nada casa; aviso "valores não encontrados no CSV" quando só parte casa; entradas `catch_all` silenciosas. As duas mensagens de aviso são travadas por igualdade literal completa.
- `outros_warning`: mensagem completa com contagem e orientação.
- `base_config_stem`: `1.1`→`inms-01`, `1.9`→`inms-09`, `1.14`→`inms-14`; chaves fora do formato `1.<n>` → `ValueError` com `inms_key` na mensagem.

Validação: `uv run pytest` 608 passed (34 skipped; +22 novos sobre os 586 anteriores), cobertura total 89.70% (gate 85%); `categoria_filter.py` passou para 96% de cobertura. `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check` e `xenon src --max-absolute F --max-average C` todos verdes.