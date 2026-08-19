# Formato do ROM Markdown

Cada indicador medido gera um ROM (`<id>.md`). O template é **genérico** com
seções fixas; só a **memória de cálculo** varia por shape. Renderizado em
`src/pyauditor/rom/render.py`.

## Seções fixas

1. **Cabeçalho** — `# ROM — <contractual_id> [— <asset>] (<name>)`, contrato, órgão.
2. **População** — linhas lidas e linhas aceitas.
3. **Rejeições** — tabela `ID | Motivo` (do `QualityGateReport`); `—` se nenhuma.
4. **Memória de cálculo** — seção por shape (abaixo).
5. **Resultado vs meta** — meta (`operator value%`), conformidade, penalidade
   em pontos.

Exemplo (shape `ratio`):

```markdown
# ROM — INMS 1.1 (Incidentes atendidos dentro do prazo)

**Contrato:** 40/2022 - Ministério Cultura
**Órgão:** MinC

## População
- Linhas lidas: 175
- Linhas aceitas: 175

## Rejeições
| ID | Motivo |
|---|---|
| — | nenhuma rejeição |

## Memória de cálculo
- Numerador: 171.0
- Denominador: 175.0
- Resultado: 97.71%

## Resultado vs meta
- Meta: >= 98.0%
- Resultado: 97.71% — **não conforme**
- Penalidade: 222.14 pontos
```

## Memória de cálculo por shape

### `ratio`

`Numerador` / `Denominador` / `Resultado`.

### `segmented_ratio`

Tabela `Categoria | Numerador | Denominador | Resultado | Penalidade` + soma das
penalidades.

### `count_difference`

`QRC (recomendados)` / `QCSI (implantados)` / `CNI = QRC − QCSI`.

### `external_catalog_sum`

Tabela `Ocorrência | Item Anexo E | Descrição | Pontos` + `Σ Pontos_NMS`.

### `precomputed_table`

Tabela `Ativo | Resultado | Penalidade` + soma das penalidades.

## Sem meta percentual (`external_catalog_sum`, ou `precomputed_table` ponto)

A seção **Resultado vs meta** mostra `Meta: não aplicável (soma de pontos, ver
Anexo E) — **conforme|não conforme**` e a penalidade.

## Fontes primárias

- `src/pyauditor/rom/render.py` — renderização.
- `docs/spec/inms-pipeline.md` §7 (exemplos INMS 1.1 e 1.8).