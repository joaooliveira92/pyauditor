from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import assert_type
from unittest.mock import patch

from pyauditor.cli.measure import run_measure


def _cfg(id_: str, contractual: str) -> SimpleNamespace:
    return SimpleNamespace(indicator=SimpleNamespace(id=id_, contractual_id=contractual))

def test_happy_path(tmp_path: Path) -> None:
    cfg_dir = tmp_path / "configs"; cfg_dir.mkdir()
    data_dir = tmp_path / "input"; data_dir.mkdir()
    out_dir = tmp_path / "roms"; out_dir.mkdir()
    configs = [_cfg("ind_a", "C-A"), _cfg("ind_b", "C-B")]
    result_ok = SimpleNamespace(hard_failure=False)
    result_fail = SimpleNamespace(hard_failure=True)

    with patch("pyauditor.cli.measure.discover_configs", return_value=configs), \
         patch("pyauditor.cli.measure.measure", side_effect=[result_ok, result_fail]), \
         patch("pyauditor.cli.measure.render_rom", return_value="# ROM"), \
         patch("pyauditor.cli.measure.summarize", return_value=SimpleNamespace(to_dict=lambda: {})):
        code = run_measure("2026-06", cfg_dir, data_dir, out_dir)
        assert_type(code, int)
        assert code == 1  # one hard_failure
        assert (out_dir / "2026-06" / "ind_a.md").read_text(encoding="utf-8") == "# ROM"
        assert (out_dir / "2026-06" / "ind_b.md").exists()
        assert (out_dir / "2026-06" / "ind_a.json").exists()

def test_no_configs_returns_1(tmp_path: Path) -> None:
    with patch("pyauditor.cli.measure.discover_configs", return_value=[]):
        assert run_measure("2026-06", tmp_path, tmp_path, tmp_path) == 1

def test_invalid_competencia_rejected(tmp_path: Path) -> None:
    assert run_measure("2026/06", tmp_path, tmp_path, tmp_path) == 1
    assert run_measure("../../etc", tmp_path, tmp_path, tmp_path) == 1
    assert run_measure("2026-13-extra", tmp_path, tmp_path, tmp_path) == 1

def test_sanitize_id_prevents_traversal(tmp_path: Path) -> None:
    cfg = _cfg("../../evil", "C-EVIL")
    with patch("pyauditor.cli.measure.discover_configs", return_value=[cfg]), \
         patch("pyauditor.cli.measure.measure", return_value=SimpleNamespace(hard_failure=False)), \
         patch("pyauditor.cli.measure.render_rom", return_value="x"), \
         patch("pyauditor.cli.measure.summarize", return_value=SimpleNamespace(to_dict=lambda: {})):
        code = run_measure("2026-06", tmp_path, tmp_path, tmp_path)
        assert code == 0
        # sanitized, not traversing
        assert (tmp_path / "2026-06" / "evil.md").exists()
        assert not (tmp_path / "evil.md").exists()

def test_mkdir_oserror_returns_1(tmp_path: Path) -> None:
    cfg = _cfg("a", "C-A")
    with patch("pyauditor.cli.measure.discover_configs", return_value=[cfg]), \
         patch.object(Path, "mkdir", side_effect=OSError("ro")):
        assert run_measure("2026-06", tmp_path, tmp_path, tmp_path) == 1

def test_write_oserror_marks_hard_failure(tmp_path: Path) -> None:
    cfg = _cfg("a", "C-A")
    with patch("pyauditor.cli.measure.discover_configs", return_value=[cfg]), \
         patch("pyauditor.cli.measure.measure", return_value=SimpleNamespace(hard_failure=False)), \
         patch("pyauditor.cli.measure.render_rom", return_value="x"), \
         patch.object(Path, "write_text", side_effect=OSError("disk full")):
        assert run_measure("2026-06", tmp_path, tmp_path, tmp_path) == 1

def test_measure_exception_continues(tmp_path: Path) -> None:
    cfgs = [_cfg("a", "C-A"), _cfg("b", "C-B")]
    with patch("pyauditor.cli.measure.discover_configs", return_value=cfgs), \
         patch("pyauditor.cli.measure.measure", side_effect=RuntimeError("boom")), \
         patch("pyauditor.cli.measure.render_rom", return_value="x"):
        assert run_measure("2026-06", tmp_path, tmp_path, tmp_path) == 1