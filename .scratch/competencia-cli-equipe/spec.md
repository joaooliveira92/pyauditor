# Spec: Competência da CLI, filtro de período e equipe.csv

Mapa: `.scratch/competencia-cli-equipe/map.md`. Decisões tomadas em sessões de wayfinder (2026-08-21) e aprovadas pelo humano; os tickets 01–04 guardam o detalhe de cada uma.

## 0. Resumo

O pipeline deriva Competência e Período de aferição exclusivamente da competência posicional obrigatória da CLI, filtra todo dataset à janela do mês, enterra os campos correspondentes na capa, passa a ler os responsáveis de `input/equipe.csv` e expõe `--strict` para endurecer o tratamento de linhas sem prova de período. Glossário: "Período de aferição" e "Equipe" já estão em `CONTEXT.md`.

## 1. Derivação do período

- Módulo novo `src/pyauditor/periodo.py`:
  - `@dataclass(frozen=True) PeriodoAfericao(inicio: date, fim: date)`;
  - `mes_bounds(competencia: str) -> PeriodoAfericao` (primeiro ao último dia do mês; `calendar.monthrange`, ano bissexto incluso);
  - função pura de filtro (§2).
- `excel/capa.py` deleta sua `_mes_bounds` privada e importa de `periodo.py`. Engine/cli nunca dependem de excel.
- Exemplos fixados pelo humano:

```text
run 2026-06 --orgao both → Competência '2026-06', início 01/06/2026, fim 30/06/2026
run 2025-12 --orgao both → Competência '2025-12', início 01/12/2025, fim 31/12/2025
```

Nada lê esses valores da capa; nada infere dos dados.

## 2. Filtro de período — um cérebro, três chamadas

- Declaração por indicador: `source.period_column` no YAML (opcional no modelo pydantic). **Obrigatória na execução**: quando o chamador passa um `PeriodoAfericao` (todo fluxo real), Source sem `period_column` é erro acionável apontando o arquivo YAML. Testes unitários que chamam `measure()` direto sem período não são afetados.
- Formato da célula inferido entre os dois conhecidos, disjuntos: `DD/MM/AAAA HH:MM` e `YYYY-MM`. Qualquer outro valor = linha sem data legível.
- Função pura devolve `(linhas_na_janela, dropped_out_of_period, undated_dropped)`; chamadores logam, a função não.
- Pontos de chamada (precedente `categoria_filter.py`):
  1. **split** — logo após `read_raw_csv`, ANTES de computar categorias: `row_count`, `outros` e warnings refletem o pós-filtro;
  2. **measure** — após `load_rows`, inclusive CSVs `_split` derivados (re-filtrar é idempotente; protege contra artefato órfão);
  3. **sintetico.xlsx** — após `read_raw_csv`.
- Assinaturas: `measure(..., *, periodo: PeriodoAfericao | None = None)`, `run_split(..., periodo=...)`, sintetico idem. `None` só existe em teste unitário.

## 3. Política de linhas e avisos

Flag `--strict` nos subcomandos que leem dataset (`split`, `measure`, `run`; `report` não lê dataset):

| Situação da linha | default | `--strict` |
|---|---|---|
| Data legível fora da janela | descartada | descartada |
| Célula vazia / formato desconhecido | segue para quality gates | descartada |
| Dentro da janela | mantida | mantida |

- WARN de janela vazia: quando havia linhas e NENHUMA caiu na janela — `nenhuma linha no período {início}–{fim} — o arquivo corresponde à competência?`. Emitido **1× por (órgão, arquivo bruto)**: split emite pros brutos que processa; measure emite só para whole_indicator (configs derivadas `_split` não emitem); sintetico nunca. Sem estado global.
- INFO estruturado por dataset quando misto: `{n} linha(s) fora do período descartada(s)` + `e {k} sem data legível` sob `--strict`.
- Dataset vazio de fábrica (zero linhas totais): estado legítimo de hoje preservado, nenhum aviso novo, `hard_failure` inalterado.
- Categoria splitada vazia pós-janela: continua normal.

## 4. Enterro na capa

- `ORGAO_FIELD_LABELS` perde: Competência, Período inicial/final da aferição **e** os 4 responsáveis (§6).
- Planilhas geradas (CAPA_E_CONTROLE embutida e consolidado) exibem "Período inicial da aferição" e "Período final da aferição" como duas linhas, rótulos canônicos, valores sempre derivados da CLI — lista própria de rótulos derivados, não hand-fill.
- Deleções: `validate_periodo_competencia`, `_parse_data_br` privada, chamada em `cli/report.py`; `_PUBLICATION_FIELDS` perde os dois períodos (período sempre conhecido nunca pode ser pendência impeditiva); `_CAPA_ROM_FIELDS` perde os três.
- Bootstrap: templates sem as linhas mortas. Capa antiga com campos órfãos: lida e ignorada silenciosamente.
- Consolidado `build_capa`: injeta Competência (já faz) e as duas linhas de período.

## 5. ROM e observabilidade

- `render_rom`/`render_combined_rom`/`_render_identificacao` recebem `competencia: str` e `periodo: PeriodoAfericao | None` explícitos; `capa_fields` alimenta só Responsáveis. Período exibido como `01/06/2026 a 30/06/2026`.
- Nota de proveniência (texto aprovado): "*Competência e Período da aferição são derivados do argumento --competência da CLI. Responsáveis refletem o estado da capa no momento em que este ROM foi gerado.*"
- Seção "Linhas aprovadas pelo quality gate" ganha a linha "Fora do período descartadas: N".
- `IndicatorSummary` ganha `dropped_out_of_period: int | None = None` e `undated_dropped: int | None = None` — None quando o filtro não rodou; sidecar antigo carrega pelos defaults; consolidado ignora os campos por ora.

## 6. equipe.csv — fonte única dos responsáveis

- Reader `excel/equipe.py`, padrão `objetos.py`: `EQUIPE_FILENAME = "equipe.csv"`, delimiter `,`, encoding `utf-8-sig`, cabeçalho `FUNÇÃO,NOME,SIAPE`. Dataclass `Equipe` com mapeamento função→(nome, siape) + `warnings`. Malformado (cabeçalho errado, linha sem nome, função duplicada) → `ValueError`; ausente → decisão do chamador.
- Mapeamento com normalização de caixa/acento: "Gestor do Contrato"→"Gestor do contrato"; "Fiscal Técnico"/"Fiscal Requisitante"/"Fiscal Administrativo"→respectivos campos. Sufixo "- Substituto" nunca sai do CSV.
- Valor da célula: `"Nome (SIAPE)"` (ex.: `João Antônio Carvalho Monteiro de Oliveira (1499628)`).
- Fonte única: capa embutida, consolidado (que passa a exibir os 4 responsáveis) e seção Responsáveis do ROM leem exclusivamente do Equipe.
- Equipe ausente/malformada → warning + campos vazios.
- Publication gate: responsáveis contam como satisfeitos quando presentes no Equipe lido.
- Bootstrap cria esqueleto `input/equipe.csv` (8 funções, valores vazios), idempotente como as capas.

## 7. Fluxo interativo

Herda tudo pelos comandos que já despacha; sem flag próprio nesta entrega.

## 8. Critérios de aceitação

1. Datasets mistos jun+ago rodando `2026-06`: mede só junho, INFO de descarte com contagem, sem WARN.
2. Dataset só de agosto rodando `2026-06`: WARN de janela vazia (1× por bruto), indicador medido sobre zero linhas.
3. Linhas sem data: `--strict` descarta e conta; default deixa pros quality gates.
4. YAML sem `source.period_column` no fluxo real: erro acionável citando o YAML; `measure()` unitário sem período continua passando.
5. ROM exibe Competência/período derivados e a nota nova; capa embutida e consolidado exibem períodos preenchidos pela CLI e os 4 responsáveis do equipe.csv.
6. Capas antigas com campos órfãos processam sem aviso.
7. `bootstrap` cria capas sem os campos mortos + esqueleto `equipe.csv`; rerun idempotente.
8. Sidecar novo lê sidecar antigo (defaults `None`) e vice-versa o consolidado ignora os campos novos.
9. `run 2025-12` fecha a janela em 31/12/2025 (fim de mês/ano corretos).

## 9. Inventário de testes

Quebram/atualizam:
- `tests/test_capa.py` — testes de `validate_periodo_competencia` deletados; labels sem os campos mortos.
- `tests/test_rom_render.py` — capa-sourced vira parâmetro derivado; placeholder só resta para o que continua vindo da capa.
- `tests/test_cli_report.py` — `warns_on_competencia_divergente_na_capa` deletado; fixtures de publicação sem períodos.
- `tests/test_excel_report.py` — linha "Competência" agora assertiva contra o valor derivado.

Novos:
- `tests/test_periodo.py` — `mes_bounds` (incl. 2025-12, fevereiro bissexto), filtro (mistos, vazios, ilegíveis, strict on/off), inferência dos dois formatos, erro de `period_column` ausente.
- `tests/test_equipe.py` — reader, mapeamento normalizado, duplicata/malformado, célula "Nome (SIAPE)".
- split/measure/sintetico com `periodo` — contagens, deduplicação de WARN, sidecar novo.

## 10. Docs

- README e `docs/spreadsheet.md`: campos novos/removidos da capa, `--strict`, `equipe.csv`, derivação do período.
- `CONTEXT.md`: já atualizado ("Período de aferição", "Equipe").

## Fora de escopo deste mapa

- Renomear/reestruturar colunas dos CSVs brutos do fornecedor.
- Estender `--strict` para além das linhas sem prova de período.
