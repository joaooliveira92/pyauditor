# 02 — C-02: Datas inválidas são descartadas silenciosamente e contaminam os cálculos

**Severidade:** Crítica

**Linhas afetadas:** 137–145, 284–328.

**Status:** resolved

## Problema

`_parse_dt()` retorna `None` para qualquer valor inválido, sem registro de erro,
sem contador de registros inválidos, sem distinção entre campo vazio e data
malformada, sem indicação visual na planilha e sem relatório de qualidade dos
dados.

Isso é crítico nas fórmulas que dependem dessas datas:

```python
ab_cell = sheet.cell(row=i, column=_AB, value=f"={uc}+{_PRAZO_HORAS_CORRIDAS}/24")
ag_cell = sheet.cell(row=i, column=_AG, value=f"={wc}-{uc}")
```

Quando `U` ou `W` estão vazias, o Excel trata a célula vazia como zero: `AB` pode
mostrar uma data baseada na origem serial do Excel, `AG` pode resultar em zero ou
duração inválida, e a média/mediana da Seção 8 e a classificação contratual bruta
ficam contaminadas por dados incompletos.

## Correção recomendada

O parsing estruturado de data (`parse_dt()`) não é específico do INMS 1.1 —
mover para `src/pyauditor/excel/_datetime.py` (novo módulo compartilhado) para
que outros renderers com o mesmo problema de datas vindas de CSV possam reusar.
A proteção das fórmulas `AB`/`AG` contra célula vazia, essa sim, é específica da
estrutura de colunas do INMS 1.1 e continua em `inms_1_1_audit.py`:

```python
ab_formula = f'=IF({uc}="","",{uc}+{_PRAZO_HORAS_CORRIDAS}/24)'
ag_formula = f'=IF(OR({uc}="",{wc}=""),"",{wc}-{uc})'
```

Adicionar coluna de qualidade dos dados (`OK` / `Data de abertura inválida` /
`Data limite inválida` / `Data de encerramento inválida` / `Encerramento anterior
à abertura`).

Idealmente `parse_dt()` deve retornar um resultado estruturado (ou lançar exceção
de domínio com linha/coluna) em vez de `None` silencioso.

## Critério de aceite

- [x] `excel/_datetime.py` criado com `parse_dt()` estruturado, importado por `inms_1_1_audit.py`
- [x] Fórmulas `AB`/`AG` (e equivalentes) protegidas contra célula de origem vazia
- [x] Coluna de qualidade dos dados adicionada e populada
- [x] Teste: datas vazias em U/W não geram duração/data espúria
- [x] Teste: datas malformadas são sinalizadas, não silenciosamente descartadas
- [x] Teste: encerramento anterior à abertura é sinalizado (ver também ticket 10 — M-01)

## Answer

Criado `src/pyauditor/excel/_datetime.py` com `parse_dt()` retornando
`ParsedDateTime(value, is_blank, is_malformed)` — distingue campo vazio de data
malformada, ao contrário do antigo `_parse_dt()` privado que devolvia `None`
para os dois casos.

Em `inms_1_1_audit.py`: nova coluna de apoio `AJ` ("Situação dos dados"),
populada em Python (não fórmula) com `OK` / `Data de abertura inválida` /
`Data limite inválida` / `Data de encerramento inválida` / `Encerramento
anterior à abertura`, com preenchimento vermelho quando ≠ `OK`. Fórmulas `AB`
(`=IF(U="","",U+2/24)`) e `AG` (`=IF(OR(U="",W="",W<U),"",W-U)`) protegidas
contra célula de origem vazia — `AG` também passou a excluir encerramento
anterior à abertura do resultado (em vez de gerar duração negativa), o que
cobre de brinde o critério de "não contaminar médias" do ticket 10 (M-01) para
esse caso específico.

De quebra, a tolerância de 1 minuto usada em `AC` (divergência de prazo) e no
loop de amostragem da Seção 7 passou a vir de `PRAZO_TOLERANCIA_MINUTOS`
(mesmo módulo `_datetime.py`), resolvendo também o ticket 13 (M-04) — os dois
pontos não podem mais dessincronizar.

Teste novo: `test_enriched_sheet_flags_invalid_and_inconsistent_dates` em
`tests/test_inms_1_1_audit.py`, cobrindo data de abertura malformada, data de
encerramento vazia (incidente em aberto, `OK`), encerramento anterior à
abertura, e linha totalmente válida. `uv run pytest tests/test_inms_1_1_audit.py
tests/test_excel_safety.py -q --no-cov` → 12 passed. `uv run mypy --strict`
limpo.

## Addendum (revisão 81c9a6e)

- **Abertura ausente**: linha com `DataHoraSolicitacao` vazia mas com
  encerramento era marcada `OK` mesmo sendo excluída das médias por dados
  incompletos. Novo veredito `"Data de abertura ausente"` (`elif
  solicitacao.is_blank`), distinguindo campo vazio de malformado — a fixture
  do teste acima ganhou a linha 6 cobrindo o caso.
- **Visibilidade da coluna `AJ`**: ver nota cruzada com o B-03 no ticket 20 —
  a coluna de qualidade deixou de ser ocultada para não anular a sinalização.
