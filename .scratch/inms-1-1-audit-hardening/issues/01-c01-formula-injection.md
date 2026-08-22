# 01 — C-01: Formula injection por dados não confiáveis do CSV

**Severidade:** Crítica

**Linhas afetadas:** 280–294, 479–481 e outros pontos que gravam strings vindas da
entrada.

**Status:** resolved

## Problema

Valores como número da solicitação, grupo executor, atividade e técnico são
gravados diretamente nas células via `sheet.cell(..., value=row[...])`. No
openpyxl, uma string iniciada por `=`, `+`, `-` ou `@` é interpretada como fórmula
pelo Excel ao abrir o arquivo. Um CSV contendo, por exemplo,
`=HYPERLINK("https://exemplo.invalid","Clique aqui")` pode ser incorporado como
fórmula ativa na planilha — hyperlinks maliciosos, referências externas, DDE em
ambientes antigos, manipulação visual dos resultados ou quebra deliberada das
tabelas de auditoria.

## Correção recomendada

**Não é específico do INMS 1.1** — criar `safe_excel_text()` em
`src/pyauditor/excel/_safety.py` (novo módulo compartilhado, mesmo padrão de
`_style.py`/`_csv_verbatim.py`), para que qualquer renderer que grave texto vindo
de CSV/YAML externo (não só `inms_1_1_audit.py`) possa reusar:

```python
def safe_excel_text(value: str) -> str:
    if value.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value
```

Aplicar pelo menos a: número da solicitação, grupo executor, atividade, técnico,
contrato, caminho do arquivo, labels vindas de configuração e qualquer texto
originado de CSV/YAML — em `inms_1_1_audit.py` e, oportunisticamente, nos demais
renderers de `excel/` que tenham o mesmo risco.

Importante: a sanitização deve diferenciar campos textuais de campos onde o
próprio módulo grava fórmulas internas (que começam com `=` de propósito) — não
sanitizar essas.

## Critério de aceite

- [x] `excel/_safety.py` criado com `safe_excel_text()` e docstring de módulo
      explicando quem reusa (padrão `_style.py`)
- [x] Aplicada em todos os pontos de `inms_1_1_audit.py` que gravam texto vindo do CSV/YAML
- [x] Teste: CSV com campo textual iniciado por `=`, `+`, `-`, `@` em cada coluna
      afetada — célula resultante não deve ser interpretada como fórmula
- [x] Fórmulas geradas internamente pelo módulo continuam funcionando normalmente

## Answer

Criado [safety.py](../../src/pyauditor/excel/_safety.py) com `safe_excel_text()`. Aplicada em
`inms_1_1_audit.py` nos pontos que gravam texto vindo do CSV bruto (número da
solicitação, grupo executor, atividade, técnico, "No prazo" — colunas R/S/T/X/Y
da base de apoio; grupo/nível/categoria do mapa AK:AM; categoria/nível/grupo da
tabela da Seção 4) e do config (`contract` na Seção 1) e do caminho de origem
(nota "Fonte dos dados" na Seção 1).

Não sanitizados de propósito: `justificativa`/`documento` (Seção 6, valores
fixos "Não informado") e todas as fórmulas geradas internamente pelo módulo
(começam com `=` por design).

Testes: `tests/test_excel_safety.py` (unidade da função) e um novo caso em
`tests/test_inms_1_1_audit.py`
(`test_enriched_sheet_sanitizes_formula_injection_from_raw_csv`) com CSV
malicioso ponta a ponta via `write_sintetico_workbook`. `uv run pytest
tests/test_inms_1_1_audit.py tests/test_excel_safety.py -q --no-cov` → 11
passed. `uv run mypy --strict` limpo nos dois arquivos.
