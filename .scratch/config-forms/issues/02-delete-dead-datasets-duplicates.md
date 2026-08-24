# Delete dead per-órgão datasets.yaml duplicates

- **Status:** resolved
- **Type:** wayfinder:task

## Question

`configs/{MinC,MTur}/datasets.yaml` são bit-a-bit idênticos a
`configs/_shared/datasets.yaml` e nunca são lidos pelo pipeline —
`resolve_config_dir` (`src/pyauditor/config/resolution.py`) prioriza
`_shared` sempre que o diretório existe, e existe. Confirmar (grep por
qualquer leitura direta de `configs/<orgao>/datasets.yaml` fora desse
resolver, checar testes que referenciam os arquivos) e então deletar os
dois arquivos mortos, pra ninguém editar a cópia errada à mão depois que o
formulário de `datasets.yaml` existir.

AFK — não precisa de humano, é confirmação + `git rm`.

## Answer

Confirmado: `diff` bit-a-bit dos dois arquivos contra `_shared/datasets.yaml`
não acusou diferença; grep por `MinC/datasets`/`MTur/datasets`/padrões de
caminho per-órgão fora do resolver não encontrou leitura direta em `src/`.
Os únicos hits em `tests/` (`test_cli_main.py`, `test_orchestration_run.py`)
escrevem suas próprias cópias em `tmp_path`, não tocam os arquivos reais do
repo. Removidos via `git rm configs/MinC/datasets.yaml
configs/MTur/datasets.yaml`.
