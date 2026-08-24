#!/usr/bin/env python3
"""Gate local de qualidade, opt-in e multiplataforma (Windows/macOS/Linux).

Roda as mesmas verificações que o gate de CI, mas só sobre os arquivos que
este branch realmente modificou, para que siga sendo rápido de rodar antes
de cada push. Escolha as verificações com flags; nada roda a menos que
vocé invoque este script. Nenhum hook de git, nem integração com o editor.

- `ruff check` e `ruff format --check` sobre os ficheiros .py modificados.
- `ty check` sobre os ficheiros .py modificados (opcional, --ty).
- Uma passada completa equivalente ao gate de CI (opcional, --full).

Todos os comandos rodam através de `uv`, coincidindo com `quality.yml`
para que os resultados locais coincidam com os de CI. Tudo é reportado,
nada é engolido de forma silenciosa.
"""

from __future__ import annotations

import argparse
import subprocess
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY_SOURCES = ('src', 'tests')
TY_VERSION = '0.0.73'


def changed_py_files() -> list[str]:
    """Arquivos .py modificados sob src/tests: staged, unstaged ou untracked."""
    repo = subprocess.run(
        ['git', 'status', '--porcelain'],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if repo.returncode != 0:
        print(f'::error:: git status falhou:\n{repo.stderr.strip()}')
        raise SystemExit(1)
    changed: list[str] = []
    for line in repo.stdout.splitlines():
        if len(line) < 4:
            continue
        rel = line[3:].strip().strip('"')
        if rel.startswith(PY_SOURCES) and rel.endswith('.py'):
            changed.append(rel)
    return sorted(dict.fromkeys(changed))


def _run(cmd: Sequence[str], files: Sequence[str]) -> bool:
    result = subprocess.run(
        [*cmd, *files], cwd=ROOT, capture_output=True, text=True
    )
    out = (result.stdout + result.stderr).strip()
    if result.returncode != 0 and out:
        print(out)
    return result.returncode == 0


def _uv_run(args: Sequence[str], files: Sequence[str]) -> bool:
    return _run(['uv', 'run', '--locked', *args], files)


def run_fast(files: Sequence[str], with_ty: bool) -> bool:
    ok = True
    if files:
        ok = _uv_run(['ruff', 'check'], list(files)) and ok
        ok = _uv_run(['ruff', 'format', '--check'], list(files)) and ok
        if with_ty:
            ok = _run(['uvx', f'ty@{TY_VERSION}', 'check'], list(files)) and ok
    return ok


def run_full() -> bool:
    """Espelho do quality.yml: ruff + ty sobre src/tests e a suite de tests."""
    ok = _uv_run(['ruff', 'check'], list(PY_SOURCES))
    ok = _uv_run(['ruff', 'format', '--check'], list(PY_SOURCES)) and ok
    ok = _run(['uvx', f'ty@{TY_VERSION}', 'check'], list(PY_SOURCES)) and ok
    ok = _run(['uv', 'run', '--locked', 'pytest'], []) and ok
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Verificações locais pre-push, opt-in e multiplataforma.'
    )
    parser.add_argument(
        '--ty',
        action='store_true',
        help='Incluir o ty check sobre os arquivos modificados.',
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help='Passada completa equivalente ao CI '
        '(ruff + ty + pytest sobre src/tests).',
    )
    args = parser.parse_args()

    if args.full:
        passed = run_full()
    else:
        files = changed_py_files()
        if not files:
            print(
                'Nenhun arquivo .py modificado em src/tests. Nada a verificar.'
            )
            return 0
        print(f'Verificando {len(files)} arquivos:')
        for f in files:
            print(f'  - {f}')
        passed = run_fast(files, args.ty)

    print(
        'PASSOU' if passed else 'FALHOU: corrige e volta a rodar o quickcheck.'
    )
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
