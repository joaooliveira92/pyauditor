# Formato do ROM Markdown

Cada indicador medido gera um ROM (`<id>.md`). O template é **genérico** com
seções fixas; só a **memória de cálculo** varia por shape, e a **ressalva
interpretativa** só aparece para shapes com penalidade em degraus (hoje:
`ratio`) quando há deficit real a interpretar. Renderizado em
`src/pyauditor/rom/render.py`. Espec: `.scratch/melhoria_rom/map.md`.

## Seções fixas

1. **Cabeçalho** — `# ROM — <contractual_id> [— <asset>] (<name>)`.
2. **Identificação** — contrato, órgão, competência e período (da capa, ou
   `[a preencher]`), data de processamento, versão do pipeline, versão da
   configuração (hash SHA-256 do YAML) e arquivo de origem (hash SHA-256,
   delimitador, codificação).
3. **Linhas aprovadas pelo quality gate** — linhas lidas e aprovadas, com
   ressalva de que isso não equivale à população contratual completa.
4. **Rejeições** — tabela `ID | Motivo` (do `QualityGateReport`); `—` se nenhuma.
5. **Memória de cálculo** — seção por shape (abaixo).
6. **Ressalva interpretativa** *(condicional)* — só quando `config.penalty`
   existe (hoje só `ratio`) e há pontuação apurada > 0: tabela com as 3
   leituras possíveis do incremento por degrau (linear contínua — adotada;
   degraus completos; teto), para transparência.
7. **Resultado vs meta** — meta (`operator value%`), conformidade, e
   "Pontuação apurada" em pontos (não "Penalidade" — o termo não implica
   sanção administrativa).
8. **Responsáveis** — Fiscal técnico/requisitante/administrativo e Gestor do
   contrato, lidos da capa (`capa_MinC.xlsx`/`capa_MTur.xlsx`), ou
   `[a preencher]`.
9. **Nota de rodapé** — avisa que os campos vindos da capa refletem seu
   estado no momento em que o ROM foi gerado, não um valor definitivo.

Exemplo (shape `ratio`, INMS 1.1 — 171/175 no prazo, capa preenchida):

```markdown
# ROM — INMS 1.1 (Incidentes atendidos dentro do prazo)

## Identificação
- Contrato: 40/2022 - Ministério da Cultura
- Órgão: MinC
- Competência: 2026-06
- Período da aferição: 01/06/2026 a 30/06/2026
- Data de processamento: 2026-08-19T23:12:28
- Versão do pipeline: 0.1.0
- Versão da configuração: a9cad620008f70a94984edfc8593715b7ed6d9690442e3cd7fc94e4b48255e2f
- Arquivo de origem: data.csv (SHA-256: 18f0748b9b66d6d57760d5313ee421cbc1e5fb394d21b43ccc0561726c7147a2, delimitador `;`, codificação utf-8)

## Linhas aprovadas pelo quality gate
- Linhas lidas: 175
- Linhas aprovadas: 175

> Aprovação pelo quality gate não equivale à população contratual completa
> (registros podem ser rejeitados por critérios estruturais que não decidem
> se pertencem ao universo do indicador).

## Rejeições
| ID | Motivo |
|---|---|
| — | nenhuma rejeição |

## Memória de cálculo
- Numerador: 171.0
- Denominador: 175.0
- Resultado: 97.71%

## Ressalva interpretativa
| Leitura | Fórmula | Pontuação apurada |
|---|---|---|
| Linear contínua (adotada) | base + (déficit / passo) × pontos_degrau | 222.14 |
| Degraus completos | base + ⌊déficit / passo⌋ × pontos_degrau | 205.00 |
| Qualquer fração inicia novo degrau | base + ⌈déficit / passo⌉ × pontos_degrau | 225.00 |

> A leitura linear contínua é a metodologia adotada por este pipeline. As
> demais leituras são apresentadas para transparência e não foram validadas
> formalmente pela gestão contratual/assessoria jurídica.

## Resultado vs meta
- Meta: >= 98.0%
- Resultado: 97.71% — **não conforme**
- Pontuação apurada: 222.14 pontos

> "Pontuação apurada" não implica sanção administrativa — ver processo
> sancionador próprio, se cabível.

## Responsáveis
- Fiscal técnico: Fulano de Tal
- Fiscal requisitante: Beltrano de Souza
- Fiscal administrativo: Ciclana Pereira
- Gestor do contrato: Sicrano Lima

---
*Competência, período e responsáveis refletem o estado da capa no momento em que este ROM foi gerado — não são valores definitivos.*
```

## Memória de cálculo por shape

(inalterado — só essa seção varia por shape)

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
Anexo E) — **conforme|não conforme**` e a pontuação apurada.

## Capa (`read_capa_fields`)

`Competência`, `Período inicial/final da aferição` e os 4 campos de
`Responsáveis` vêm de `pyauditor.excel.capa.read_capa_fields(capa_path)` —
lido em `cli/measure.py` a partir de `capa_MinC.xlsx`/`capa_MTur.xlsx`
(resolvido por `--capa-path`, mesma convenção de `bootstrap`/`report`). Capa
ausente ou campo vazio não bloqueia `measure`: gera um aviso e o ROM mostra
`[a preencher]` no campo. Ver `MeasurementProvenance` em
`engine/pipeline.py` para os demais metadados de identificação (hash,
versões, timestamp).

## Fontes primárias

- `src/pyauditor/rom/render.py` — renderização.
- `src/pyauditor/engine/pipeline.py` — `MeasurementProvenance`, `measure()`.
- `.scratch/melhoria_rom/map.md` — espec desta reescrita.
- `docs/spec/inms-pipeline.md` §7 (exemplos INMS 1.1 e 1.8, pré-reescrita).
