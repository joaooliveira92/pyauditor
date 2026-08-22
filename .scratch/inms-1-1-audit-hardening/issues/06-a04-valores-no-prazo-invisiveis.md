# 06 — A-04: Valores de "No prazo" diferentes de "S" e "N" ficam invisíveis

**Severidade:** Alta

**Linhas afetadas:** 293, 642, 959–961.

**Status:** needs-triage

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

- [ ] Normalização/validação de "No prazo" implementada na fronteira (fail-fast ou categoria "INVÁLIDO")
- [ ] Verificação `IAP = dentro + fora` adicionada à planilha
- [ ] Teste: valores `S`, `N`, `s`, `n`, espaços e valores inválidos (matriz de testes do spec.md)
