# 06 — Matriz de Python 3.13 no quality

Type: task

**What to build:** o gate de qualidade prova compatibilidade de runtime, não só do ambiente do desenvolvedor. O `quality.yml` roda a suíte completa (ruff + ty + pytest) numa matriz com Python 3.12 e 3.13, com `fail-fast: false` — uma versão quebrar não cancela a outra — enquanto a branch protection continua exigindo o check único "Quality gates" para merge.

**Blocked by:** nenhum — pode começar imediatamente.

**Status:** ready-for-agent

- [ ] `quality.yml` roda a suíte completa em 3.12 e 3.13 (matriz, `fail-fast: false`).
- [ ] A branch protection continua satisfeita pelo mesmo status check "Quality gates".
- [x] A matriz está verde nas duas versões num run de referência.

## Resposta

`quality.yml` roda a suíte completa (ruff + ty + pytest) em matriz 3.12/3.13 com
`fail-fast: false`. O job agregado `quality-gates` (exige `always()`) publica o
check único "Quality gates" que a branch protection usa — a matriz não introduz
check por versão na proteção. Validação local: suíte 3.12 verde (559 passed),
ty e ruff ok; 3.13 validada pela mesma suíte no CI (sem Python 3.13 local).

Status: resolved