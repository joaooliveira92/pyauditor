"""`engine.version.pipeline_version` — os três caminhos da versão do pipeline
(ticket reducao-friccao/03), sem depender do estado real do ambiente.

Cobre: pacote instalado via `importlib.metadata`, commit git via `subprocess`
mockado e o marcador fixo quando ambos falham.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError
from types import SimpleNamespace
from typing import NoReturn

import pytest

from pyauditor.engine.version import pipeline_version

_GIT_ARGS = ['git', 'rev-parse', '--short', 'HEAD']


@pytest.fixture(autouse=True)
def _clear_version_cache() -> None:
    pipeline_version.cache_clear()


def _not_installed(_name: str) -> NoReturn:
    raise PackageNotFoundError


def _raise_oserror() -> None:
    raise OSError('git não encontrado')


def _raise_called_process_error() -> None:
    raise subprocess.CalledProcessError(returncode=128, cmd=_GIT_ARGS)


def _raise_timeout() -> None:
    raise subprocess.TimeoutExpired(cmd=_GIT_ARGS, timeout=5)


def test_installed_package_wins_via_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr('importlib.metadata.version', lambda _name: '0.1.0')

    assert pipeline_version() == '0.1.0'


def test_git_commit_when_package_not_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr('importlib.metadata.version', _not_installed)
    monkeypatch.setattr(
        'pyauditor.engine.version.subprocess.run',
        lambda *_args, **_kwargs: SimpleNamespace(stdout='abc1234\n'),
    )

    assert pipeline_version() == 'abc1234'


@pytest.mark.parametrize(
    'subprocess_failure',
    [
        pytest.param(_raise_oserror, id='git-falta-no-path'),
        pytest.param(_raise_called_process_error, id='commit-falhou'),
        pytest.param(_raise_timeout, id='timeout-5s'),
    ],
)
def test_fixed_marker_when_both_fail(
    monkeypatch: pytest.MonkeyPatch,
    subprocess_failure: Callable[[], None],
) -> None:
    monkeypatch.setattr('importlib.metadata.version', _not_installed)

    def _failing_run(*_args, **_kwargs) -> SimpleNamespace:
        subprocess_failure()
        return SimpleNamespace(stdout='')

    monkeypatch.setattr('pyauditor.engine.version.subprocess.run', _failing_run)

    assert pipeline_version() == 'dev'
