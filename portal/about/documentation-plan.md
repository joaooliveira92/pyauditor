# Plano de documentação — portal pyauditor

> Plano de informação para o portal de documentação do `pyauditor` (contrato
> 40/2022 — Ministério da Cultura). Escrito a partir da inspeção do código-fonte
> real, da spec `docs/spec/inms-pipeline.md` e dos configs de produção
> (`configs/inms-<n>.yaml`).

## 1. Auditores e trabalhos a executar

**Auditório primário:** fiscal técnico do contrato e novos desenvolvedores do
pipeline. **Auditório secundário:** gestão do contrato que precisa entender o
fluxo de apuração e as saídas.

Principais tarefas (jobs-to-be-done):

- Rodar a apuração mensal de ponta a ponta (bootstrap → measure → report).
- Entender o que o pipeline calcula e como os 14 indicadores são classificados.
- Adicionar um novo indicador/serviço sem mudar o motor.
- Interpretar os artefatos gerados: ROM Markdown, sumário JSON, planilha final.
- Diagnosticar e recuperar de falhas de medição.

## 2. Navegação proposta

```text
docs/
  index.md                                   Portal — visão geral + mapa
  about/documentation-plan.md                Este plano
  getting-started/
    index.md                                 Roteiro do novo usuário
    installation.md                         instalar e verificar
    quickstart.md                           apurar uma competência de ponta a ponta
  concepts/
    index.md                                Conceitos
    pipeline.md                             Arquitetura do pipeline
    shapes.md                               Os 5 shapes de cálculo
    data-layout.md                          Organização de entrada/saída no disco
  reference/
    cli.md                                  CLI bootstrap/measure/report
    config.md                               Schema dos YAML `inms-<n>.yaml`
    rom.md                                  Formato do ROM Markdown
    summary.md                              Sumário JSON (lido pelo report)
    excel.md                                Abas da planilha final
  guides/
    bootstrap-capa.md                       Preencher a capa
    measure-indicators.md                   Rodar a medição
    build-report.md                         Consolidar o Excel final
    add-indicator.md                        Adicionar um indicador
  operations/
    troubleshooting.md                      Falhas conhecidas e recuperação
  glossary.md                               Glossário de domínio
```

## 3. Inventário de páginas

| Página | Tipo | Público | Objetivo | Fonte de verdade |
|---|---|---|---|---|
| `getting-started/index.md` | índice | todos | roteiro dos próximos passos | — |
| `getting-started/installation.md` | how-to | desenvolvedores, técnico | instalar com `uv` e verificar a CLI | `README.md`, `pyproject.toml` |
| `getting-started/quickstart.md` | how-to | técnico | rodar uma competência completa | `src/pyauditor/cli/*.py` |
| `concepts/pipeline.md` | explicação | desenvolvedor | arquitetura e fluxo | `src/pyauditor/engine/pipeline.py`, spec §3–§6 |
| `concepts/shapes.md` | explicação | dev e técnico | os 5 shapes e quando cada um é usado | spec §2–§3, `configs/*.yaml` |
| `concepts/data-layout.md` | explicação | dev e técnico | onde vivem inputs/configs/saídas | `measure.py`, `.gitignore` |
| `pipeline-guide/cli.md` | referência | dev | comandos, flags, defaults e saídas | `cli/main.py` |
| `pipeline-guide/config.md` | referência | dev | schema YAML de indicador | `config/models.py`, `config/*.yaml` |
| `pipeline-guide/rom.md` | referência | dev | seções fixas + memória por shape | `rom/render.py` |
| `pipeline-guide/summary.md` | referência | dev | campos do JSON | `rom/summary.py` |
| `pipeline-guide/excel.md` | referência | técnico | abas da planilha | `excel/report.py`, `docs/spreadsheet.md` |
| `guides/bootstrap-capa.md` | how-to | técnico | criar e preencher a capa | `cli/bootstrap.py`, `excel/capa.py` |
| `guides/measure-indicators.md` | how-to | técnico | rodar a medição e ler os ROMs | `cli/measure.py` |
| `guides/build-report.md` | how-to | técnico | consolidar o Excel final | `cli/report.py`, `excel/report.py` |
| `guides/add-indicator.md` | how-to | dev | novo indicador sem tocar o motor | `config/models.py`, fixtures |
| `operations/troubleshooting.md` | referência | dev e técnico | falhas e recuperação | código, spec §11–§13 |
| `glossary.md` | referência | todos | termos do domínio | spec, `docs/spreadsheet.md` |

## 4. Rastreabilidade fonte → página

Cada página cita a fonte primária (arquivo de código, config ou spec). Nada é
inventado: fatos não confirmados são marcados como TODO/assunção. Ver o style
guide em `.agents/skills/zensical-documentation-skill/references/style-guide.md`.

## 5. Decisões de terminologia

- Manter os nomes internos do código como termos canônicos: `bootstrap`,
  `measure`, `report`, `shape`, `ROM`, `competência` (português), `quality
  gates`, `memoria de cálculo`.
- Header dos ROMs usa acentos; o portal escreve em português para o público
  do contrato, adotando a grafia já usada no repo.

## 6. Desconhecidos e TODOs

- Seções em aberto da spec (fog do 1.8/1.10 — schema de entrada, fórmula
  MinC/MTur para 1.4/1.5/1.14) permanecem sem resposta nas páginas; são citadas
  como pergunta em aberto nos locais pertinentes (troubleshooting, shapes).
- O comportamento de `zensical build` não verifica (Zensical não instalado no
  repo) — as páginas não declaram um build Zensical.

## 7. Critérios de aceitação

- Um técnico novo completa o quickstart sem voltar ao código-fonte.
- Cada plano de página tem procedimento com verificação explícita.
- Links de Markdown relativos resolvem; nenhum link quebrado.
- `scripts/validate_docs.py` passa.
- Nenhuma informação fabricada; TODOs explícitos para o que falta.