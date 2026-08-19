from pathlib import Path

from pyauditor.cli.bootstrap import run_bootstrap


def test_run_bootstrap_creates_capa_and_returns_0(tmp_path: Path) -> None:
    capa_path = tmp_path / "capa.xlsx"

    exit_code = run_bootstrap(capa_path)

    assert exit_code == 0
    assert capa_path.exists()


def test_run_bootstrap_is_a_noop_when_capa_exists(tmp_path: Path) -> None:
    capa_path = tmp_path / "capa.xlsx"
    run_bootstrap(capa_path)
    mtime_before = capa_path.stat().st_mtime_ns

    exit_code = run_bootstrap(capa_path)

    assert exit_code == 0
    assert capa_path.stat().st_mtime_ns == mtime_before
