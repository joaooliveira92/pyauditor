# 06 — A-04: Valores de "No prazo" diferentes de "S" e "N" ficam invisíveis

**Severidade:** Alta

**Linhas afetadas:** 293, 642, 959–961.

**Status:** resolved

## Problema

`COUNTIF(...,"S")` e `COUNTIF(...,"N")` usam correspondência exata, mas o IAP é
calculado independentemente via `COUNTA(...)`. Valores como `"s"`, `"n"`, `"S "`,
`"Sim"`, `"Não"`, vazio ou `"N/A"` entram no denominador (IAP) mas não entram nem
em "dentro do prazo" nem em "fora do prazo". A identidade esperada
`IAP = dentro do prazo + fora do prazo` pode deixar de valer, sem que a planilha
sinalize isso.

## Correção recomendada

Avaliar ao implementar: se outros relatórios ITSM do pipeline usarem o mesmo
vocabulário "No prazo" (S/N), extrair `normalize_no_prazo()` para um módulo
compartilhado (`excel/_datetime.py` ou um novo `excel/_itsm.py`); caso contrário,
manter local a `inms_1_1_audit.py`. Ver nota de reuso em `spec.md`.

Normalizar em Python antes de gravar:

```python
def _normalize_no_prazo(value: str) -> str:
    normalized = value.strip().upper()
    if normalized not in {"S", "N"}:
        raise ValueError(...)
    return normalized
```

Alternativa: criar categoria explícita `"INVÁLIDO"` e seção de qualidade de
dados. Adicionar verificação na planilha:

```
=IF(B13=C13+D13,"OK","DIVERGÊNCIA DE CLASSIFICAÇÃO")
```

## Critério de aceite

- [x] Normalização/validação de "No prazo" implementada na fronteira (fail-fast ou categoria "INVÁLIDO")
- [x] Verificação `IAP = dentro + fora` adicionada à planilha
- [x] Teste: valores `S`, `N`, `s`, `n`, espaços e valores inválidos (matriz de testes do spec.md)

## Answer

Escolhido fail-fast (não a categoria "INVÁLIDO" alternativa): `_normalize_no_prazo()`
em `inms_1_1_audit.py` faz `strip().upper()` e levanta `ValueError` (citando o
Nº Solicitação da linha) para qualquer valor fora de `{"S", "N"}`. Mantida local
a este módulo — não há hoje outro renderer ITSM reusando esse vocabulário
S/N (nota de reuso do spec.md). `write_sheet()` aplica a normalização a todas
as `rows` antes de montar a base de apoio, então a coluna `_X` só recebe "S" ou
"N" (nunca "s", "Sim", vazio etc.), preservando a identidade IAP = dentro + fora
por construção.

Mesmo com a normalização na fronteira, a verificação `IAP = dentro do prazo +
fora do prazo` foi adicionada como checagem redundante na Seção 5 (célula ao
lado de "Verificação cruzada (Seção 5 = Seção 2/3)"), com o mesmo padrão de
formatação condicional OK/DIVERGÊNCIA — cinto e suspensório caso a normalização
seja removida ou contornada no futuro.

`sintetico.py` captura o `ValueError` (junto com os demais erros de validação
deste módulo) e degrada para o renderer genérico, sem derrubar o workbook.

Testes: `test_no_prazo_invalid_or_variant_values` (parametrizado com `s`, `n`,
` S `, ` N `, `Sim`, `Não`, `N/A`, vazio) e `test_no_prazo_lowercase_and_spaces_are_normalized`
em `tests/test_inms_1_1_audit.py`.
