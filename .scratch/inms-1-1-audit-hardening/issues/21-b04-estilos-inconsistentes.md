# 21 — B-04: Estilos não são aplicados consistentemente

**Severidade:** Baixa

**Status:** resolved

## Problema

Na Seção 5, `pct` e tempo de N1/N2/N3 não recebem explicitamente `BODY_FONT`,
enquanto outros campos recebem. Não altera o cálculo, mas reduz consistência
visual.

## Correção recomendada

Aplicar `BODY_FONT` de forma consistente a todas as células de dados da Seção 5.

## Critério de aceite

- [x] `pct` e tempo de N1/N2/N3 recebem `BODY_FONT` como os demais campos da Seção 5

## Answer

Confirmado no código atual (não estava corrigido por nenhum ticket anterior):
o laço de fonte das linhas N1/N2/N3 só cobria `(linhas, dentro, fora_c)`,
deixando `pct` e `tempo` com a fonte padrão do openpyxl — ao contrário da linha
"Sem nível" logo abaixo, que já incluía `pct`/`tempo` no seu próprio laço.
Corrigido para `for c in (linhas, dentro, fora_c, pct, tempo): c.font = BODY_FONT`.

Teste: `test_section_5_nivel_rows_use_body_font_consistently` em
`tests/test_inms_1_1_audit.py`, verificando `font.name == "Arial"` nas colunas
`pct`/`tempo` da linha "N1".
