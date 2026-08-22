# 17 — M-08: Falta de atomicidade na criação da aba

**Severidade:** Média

**Status:** needs-triage

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

- [ ] `create_sheet_atomic()` implementado em `excel/_workbook.py` e usado por `write_sheet()`
- [ ] Teste: erro forçado no meio da escrita não deixa aba parcial no workbook
