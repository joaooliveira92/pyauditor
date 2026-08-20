from pathlib import Path
from unittest.mock import patch

from pyauditor.cli.bootstrap import run_bootstrap


def test_run_bootstrap_creates_capa_and_returns_0(tmp_path: Path) -> None:
    capa_path = tmp_path / "capa.xlsx"

    result = run_bootstrap(capa_path, "MinC")

    assert result.status == "done"
    assert result.created is True
    assert capa_path.exists()


def test_run_bootstrap_is_a_noop_when_capa_exists(tmp_path: Path) -> None:
    capa_path = tmp_path / "capa.xlsx"
    run_bootstrap(capa_path, "MinC")
    mtime_before = capa_path.stat().st_mtime_ns

    result = run_bootstrap(capa_path, "MinC")

    assert result.status == "done"
    assert result.created is False
    assert capa_path.stat().st_mtime_ns == mtime_before


def test_run_bootstrap_converts_unexpected_exception_to_error_result(tmp_path: Path) -> None:
    capa_path = tmp_path / "capa.xlsx"

    with patch("pyauditor.cli.bootstrap.bootstrap_capa", side_effect=ValueError("boom")):
        result = run_bootstrap(capa_path, "MinC")

    assert result.status == "error"
    assert result.error_message is not None
    assert "boom" in result.error_message
