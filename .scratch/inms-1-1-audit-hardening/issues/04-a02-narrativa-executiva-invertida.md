# 04 — A-02: Texto executivo sempre afirma que o resultado ficou abaixo do mínimo

**Severidade:** Alta

**Linhas afetadas:** 452–456.

**Status:** resolved

## Problema

A fórmula `CONCATENATE(...)` usa `ABS(B25)` e sempre escreve "abaixo do mínimo
necessário", mesmo quando `B25` é positivo (meta superada). Exemplo: mínimo
necessário 95, IADP 98, margem +3 → o texto gerado diz "O resultado ficou 3
incidente(s) abaixo do mínimo necessário", o que é um erro material de auditoria
e contradiz a situação exibida na Seção 2.

## Correção recomendada

Narrativa condicional:

```python
=IF(
    B25<0,
    CONCATENATE(...,ABS(B25)," incidente(s) abaixo do mínimo necessário."),
    IF(
        B25=0,
        CONCATENATE(...," exatamente no mínimo necessário."),
        CONCATENATE(...,B25," incidente(s) acima do mínimo necessário.")
    )
)
```

## Critério de aceite

- [x] Fórmula da linha ~452–456 corrigida com narrativa condicional (abaixo / exatamente / acima)
- [x] Teste: meta atingida com margem positiva → narrativa diz "acima do mínimo"
- [x] Teste: meta exatamente atingida → narrativa diz "exatamente no mínimo"
- [x] Teste: meta não atingida → narrativa diz "abaixo do mínimo" (comportamento atual, preservado)

## Answer

`A26` (Seção 3) agora é `IF(B13=0,"Sem incidentes...",IF(B25<0,<abaixo>,IF(B25=0,<exato>,<acima>)))`,
com três chamadas `CONCATENATE(...)` completas — uma por desfecho — construídas
em Python via um helper `_narrativa(desfecho)` que compartilha o prefixo comum
("Com N incidentes, seriam necessários pelo menos M... resultado ficou ") e
completa com o texto certo por ramo. `ABS(B25)` só aparece no ramo `B25<0`
agora; os ramos `B25=0` e `B25>0` usam texto próprio ("exatamente no mínimo" /
"`B25` incidente(s) acima do mínimo"). Adicionado também o caso `B13=0`
("Sem incidentes abertos... indicador não mensurável"), consistente com a
regra do ticket 03 (A-01).

Verificação de sintaxe da fórmula composta feita manualmente char-a-char (sem
LibreOffice disponível no ambiente para recálculo real — `soffice`/`libreoffice`
não encontrados) e via impressão direta do valor da célula.

Teste: `test_section_3_narrativa_reflects_actual_margin_sign` em
`tests/test_inms_1_1_audit.py`, verificando a presença dos três ramos
`CONCATENATE` e do texto correto em cada um. `uv run pytest
tests/test_inms_1_1_audit.py tests/test_excel_safety.py -q --no-cov` → 15
passed. `uv run mypy --strict` limpo.

Nota para follow-up: a validação de que a fórmula *calcula* corretamente
(não só que é sintaticamente válida) depende do smoke test de recálculo via
motor externo previsto no ticket 08 (A-06) — ambiente atual não tem
LibreOffice/Excel para rodar esse smoke test.
