# Spec — Single-source para configs de INMS (escalabilidade por órgão)

## Contexto
Hoje `configs/MinC/` e `configs/MTur/` duplicam 14 YAMLs base (`inms-01.yaml`…`inms-14.yaml`) + `datasets.yaml` idêntico, diferindo só em `scope.orgao`/`contract`, `acceptance_test` (números da competência 06/2026) e `categorias.yaml` (literais de Grupo executor). `split` materializa CSVs filtrados em `input/_split/` + YAMLs derivados `inms-*.*.yaml` (gitignored mas trackeados), triplicando I/O para INMS segmentados. O motor (`shape` discriminated union + `QualityGateRunner` + `DatasetManifest`) já é simples e eficiente — o gargalo é organização de arquivos, não verificação.

Referências: avaliação profunda de 2026-08-21 sobre `configs/`, ADR 0002 (`Config por categoria gerada pelo split`), `CONTEXT.md` (termos Órgão/Competência/Categoria/Grupo executor/ROM), `docs/spec/inms-pipeline.md` §§2-4.

## Destino
Um único diretório canônico `configs/_shared/` com os 14 indicadores (sem órgão), um `datasets.yaml` único e `acceptance_test` fora dos YAMLs de produção. `órgão` vira dimensão de execução (`measure --orgao MinC`), não de arquivo. `split` vira filtro lógico em memória (sem `_split/` físico). Clone fresco determinístico, sem estado derivado no repo.

## Fora de escopo
- Novo `shape` ou mudança de fórmula do Anexo D.
- Troca de `Pydantic + QualityGateRunner` por framework externo (`pandera` etc.).
- Terceiro órgão além de MinC/MTur nesta entrega (a estrutura deve suportar, mas não popular).

## Decisões
- Single-source + overlay por órgão (Alternativa A da avaliação) — mantém YAML declarativo para fiscal.
- `acceptance_test` sai de produção e vai para `tests/acceptance/<orgao>/<competencia>.yaml`.
- `split` não materializa mais artefatos em disco; `categoria_filter.compute_categoria_values` continua como única fonte de partição.
- Descoberta de configs determinística via `configs/_shared/*.yaml` + injeção de `scope.orgao` em runtime.

## Riscos
- Drift silencioso se alguém editar base antiga sem rodar `split` — mitigado por `git rm --cached` dos derivados + teste de invariantes.
- Regressão nos números de 06/2026 — mitigado por teste de não-regressão com snapshots.
