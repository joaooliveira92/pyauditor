# Adicione um indicador

Use este procedimento para apurar um novo indicador sem alterar o motor. Cada
indicador é declarativo: um YAML + um CSV.

## Pré-requisitos

- Entenda os [shapes de cálculo](../concepts/shapes.md) e o
  [schema de config](../reference/config.md).

## Procedimento

1. Coloque o CSV da competência em `input/<orgao>/<ano>/<mês>/` e registre-o no
   manifesto se for um novo dataset:

   ```yaml
   datasets:
     novo_dataset:
       file: inms-99.csv
       delimiter: ";"
       encoding: utf-8-sig
   ```

2. Crie `configs/<orgao>/inms-99.yaml` declarando: `indicator`, `scope`, `source`
   (com `dataset: novo_dataset`), `quality_gates`, `calculation` (shape),
   e, conforme o shape, `target`/`penalty`.

3. (Opcional) Adicione um `acceptance_test.expected` para o smoke test.

4. Valide a medição:

   ```bash
   uv run pyauditor measure 2026-06 --orgao MinC --config-dir configs --data-dir input --output-dir roms
   ```

## Verificação

- `roms/MinC/2026-06/INMS-99.md` e `roms/MinC/2026-06/INMS-99.json` foram criados.
- O ROM mostra população, rejeições, memória de cálculo e resultado vs meta
  coerentes.
- Rode os testes para garantir que novas configs não quebram o pipeline:

   ```bash
   uv run pytest
   ```

## Exemplos por shape

- **`ratio`** — `configs/<orgao>/inms-01.yaml` (razão simples com meta e penalidade).
- **`segmented_ratio`** — `configs/<orgao>/inms-02.yaml`.
- **`precomputed_table`** — `configs/<orgao>/inms-10.yaml` (tabela de apuração
  por linha/ativo).
- **`count_difference`** — modelo e fixture em
  `tests/fixtures/manual_entry_examples/inms-1.10-*`.
- **`external_catalog_sum`** — `tests/fixtures/manual_entry_examples/inms-1.8-*`.

## Falhas comuns

- **`source must specify exactly one of 'dataset' or 'csv'`** — um dos campos
  precisa estar presente (não ambos).
- **Shape sem `target`** (exceto `external_catalog_sum`) ou **`target` em
  `external_catalog_sum`** — erro de validação do config.
- **Campo desconhecido** — os modelos são restritos (`extra="forbid"`); um typo
  falha na carga.

## Próximos passos

- Veja [Organização dos dados](../concepts/data-layout.md) e
  [Problemas conhecidos](../operations/troubleshooting.md).