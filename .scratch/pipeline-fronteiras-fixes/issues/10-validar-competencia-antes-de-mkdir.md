# 10 — Validar `competencia` antes de qualquer efeito colateral no dispatch da CLI

**Origem:** [Cli dispatch boundary review](../../pipeline-fronteiras-review/issues/06-cli-dispatch-boundary.md)

**What to build:** `cli/main.py` não valida `competencia` no `argparse` (sem `type=`); `setup_logging` já faz `mkdir(parents=True)` incondicional usando o valor cru antes de `validate_competencia` rodar dentro de cada `run_*`. Uma `competencia` malformada já cria diretórios de log/output errados antes de qualquer validação barrar. Isso afeta todos os comandos igualmente, incluindo `split`. Mover a validação de `competencia` para antes da criação de qualquer diretório/arquivo no dispatch de `cli/main.py`.

**Blocked by:** None — can start immediately.

- [ ] Uma `competencia` malformada falha antes de criar qualquer diretório de log/output, para todos os comandos (`measure`, `bootstrap`, `report`, `consolidate`, `split`, `run`)
- [ ] Teste de regressão confirmando que nenhum diretório é criado quando `competencia` é inválida
