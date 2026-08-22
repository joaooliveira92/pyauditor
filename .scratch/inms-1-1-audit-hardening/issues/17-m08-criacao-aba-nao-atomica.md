# 17 — M-08: Falta de atomicidade na criação da aba

**Severidade:** Média

**Status:** resolved

## Problema

`write_sheet()` cria a aba no início (`sheet = workbook.create_sheet(sheet_name)`).
Se qualquer erro ocorrer depois, o workbook fica parcialmente modificado (aba
criada mas incompleta).

## Correção recomendada

**Não é específico do INMS 1.1** — qualquer `write_sheet()`-like function que
crie uma aba e a preencha em várias etapas tem o mesmo risco de estado parcial.
Criar um context manager `create_sheet_atomic(workbook, sheet_name)` em
`src/pyauditor/excel/_workbook.py` (mesmo módulo dos tickets 08/A-06 e 15/M-06):

```python
@contextmanager
def create_sheet_atomic(workbook: Workbook, sheet_name: str) -> Iterator[Worksheet]:
    sheet = workbook.create_sheet(sheet_name)
    try:
        yield sheet
    except Exception:
        workbook.remove(sheet)
        raise
```

## Critério de aceite

- [x] `create_sheet_atomic()` implementado em `excel/_workbook.py` e usado por `write_sheet()`
- [x] Teste: erro forçado no meio da escrita não deixa aba parcial no workbook

## Answer

Implementado como sugerido: `create_sheet_atomic()` em `excel/_workbook.py`
cria a aba, entrega ao bloco `with`, e remove a aba do workbook se qualquer
exceção escapar. `write_sheet()` envolve toda a escrita das 9 seções nesse
`with` — `force_recalc(workbook)` fica de propósito fora do bloco, depois que
a aba já está completa.

Testes: `test_create_sheet_atomic_yields_usable_sheet` e
`test_create_sheet_atomic_removes_sheet_on_failure` em
`tests/test_excel_workbook.py` (unitários do context manager); e
`test_write_sheet_atomic_rollback_on_duplicate_grupo` em
`tests/test_inms_1_1_audit.py`, que força o erro real do ticket 14 (M-05,
grupo mapeado em duas categorias, propagado por `compute_categoria_values`)
no meio da escrita de `write_sheet()` e confirma que o workbook não fica com
a aba `"INMS 1.1"` parcialmente criada.
