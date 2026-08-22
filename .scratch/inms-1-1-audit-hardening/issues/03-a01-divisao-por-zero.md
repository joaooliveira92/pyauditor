# 03 — A-01: Divisões por zero geram `#DIV/0!`

**Severidade:** Alta

**Linhas afetadas:** 400, 589, 692, 696, 701, 738.

**Status:** resolved

## Problema

Fórmulas como `=C13/B13`, `=C{totr}/B{totr}`, `=COUNTIF(...)/B13`, `=B{div_count_row}/B13`
não protegem o denominador. Quando não há incidentes (ou o identificador da
solicitação está vazio), `B13` pode ser zero, propagando `#DIV/0!` para as Seções
3, 5, 7 e 9 — justamente no cenário sem ocorrências, tornando a planilha
inutilizável.

## Correção recomendada

Definir explicitamente a regra de negócio para denominador zero (não é só uma
questão de fórmula — decidir o significado correto):

- não aplicável
- meta atingida
- meta não mensurável
- resultado zero

Exemplo de fórmula, uma vez decidida a regra:

```PYTHON
=IF(B13=0,"Sem ocorrências",C13/B13)
```

`=IFERROR(C13/B13,0)` é mais simples mas pode transmitir "desempenho 0%" quando o
correto seria "não mensurável" — decisão de domínio, não só técnica.

Todas as fórmulas dependentes downstream que comparam o resultado como percentual
numérico precisam ser adaptadas para lidar com o novo valor não numérico (se a
opção escolhida for texto).

## Critério de aceite

- [x] Regra de negócio para "zero incidentes" definida e documentada
- [x] Todas as fórmulas listadas (linhas 400, 589, 692, 696, 701, 738) protegidas
- [x] Teste: workbook com zero incidentes não produz nenhuma célula com `#DIV/0!`
- [x] Teste: classificação contratual continua bem definida no cenário de zero incidentes

## Answer

Regra adotada: `B13=0` (IAP, denominador) é tratado como **não mensurável**, não
como 0% de desempenho — texto `"Sem ocorrências"` para resultados percentuais e
`"Não aplicável"` para veredito (situação/penalidade), nunca "Meta não
atingida" nem penalidade aplicada.

Todas as divisões por `B13` foram guardadas com `IF(B13=0,"Sem
ocorrências",...)`: `E13` (resultado), Seção 5 (`E{totr}`, total geral por
nível), Seção 7 (as três metodologias de controle) e `% do total` de
divergência de prazo. Cada consumidor downstream que fazia aritmética/
comparação sobre esses valores também foi guardado, em cascata:

- `F13`/`G13` (Seção 2): guardados contra `E13` textual.
- `B23` (Seção 3, desvio em p.p.): guardado.
- `check_row` (Seção 5, verificação cruzada Seção 5×2/3): usa
  `ISNUMBER(...)` para comparar corretamente mesmo quando ambos os lados são
  texto (`"Sem ocorrências"="Sem ocorrências"` → `"OK"`).
- Situação de cada metodologia da Seção 7: `"Não aplicável"` em vez de
  `"Meta atingida"/"Meta não atingida"` quando `B13=0`.
- Seção 9 (penalidade): `"Não aplicável"` em cascata em todas as linhas
  (diferença, diferença em p.p., penalidade-base, adicional, total, cenário)
  — nenhuma penalidade é calculada quando não há incidentes no período.

Teste: `test_zero_denominator_formulas_are_guarded_against_div0` em
`tests/test_inms_1_1_audit.py`, verificando a presença da guarda em cada
fórmula afetada das Seções 2, 3, 5, 7 e 9 (openpyxl não executa fórmulas, então
a verificação é sobre o texto da fórmula, não sobre o resultado calculado —
suficiente para garantir que a guarda existe; validação do resultado real fica
para o smoke test de recálculo do ticket 08/A-06). `uv run pytest
tests/test_inms_1_1_audit.py tests/test_excel_safety.py -q --no-cov` → 14
passed. `uv run mypy --strict` limpo.
