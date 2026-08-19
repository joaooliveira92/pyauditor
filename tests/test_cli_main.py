from __future__ import annotations

import argparse
from pathlib import Path
from typing import assert_type
from unittest.mock import patch

import pytest

from pyauditor.cli.main import MeasureRequest, build_parser, cli_main
from pyauditor.logging import logger


def test_build_parser_typed() -> None:
    parser = build_parser()
    assert_type(parser, argparse.ArgumentParser)
    assert parser.prog == "pyauditor"


def test_measure_request_frozen_slots() -> None:
    r = MeasureRequest(
        competencia="2026-06",
        config_dir=Path("configs"),
        data_dir=Path("input"),
        output_dir=Path("roms"),
        manifest_path=Path("configs") / "datasets.yaml",
    )
    assert_type(r.competencia, str)
    with pytest.raises(AttributeError):
        r.competencia = "2026-07"  # type: ignore[misc]  # frozen


def test_cli_main_happy_path(tmp_path: Path) -> None:
    cfg, data, out = tmp_path / "c", tmp_path / "d", tmp_path / "o"
    for p in (cfg, data, out):
        p.mkdir()
    with patch("pyauditor.cli.main.run_measure", return_value=0) as m:
        code = cli_main(["measure", "2026-06", "--config-dir", str(cfg), "--data-dir", str(data), "--output-dir", str(out)])
        assert code == 0
        assert m.call_args.kwargs["competencia"] == "2026-06"
        assert m.call_args.kwargs["config_dir"] == cfg


def test_cli_main_bootstrap_dispatches_with_capa_path(tmp_path: Path) -> None:
    capa_path = tmp_path / "capa.xlsx"
    with patch("pyauditor.cli.main.run_bootstrap", return_value=0) as m:
        code = cli_main(["bootstrap", "--capa-path", str(capa_path)])
        assert code == 0
        assert m.call_args.args[0] == capa_path


def test_cli_main_bootstrap_default_capa_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    with patch("pyauditor.cli.main.run_bootstrap", return_value=0) as m:
        code = cli_main(["bootstrap"])
        assert code == 0
        assert m.call_args.args[0] == Path("capa.xlsx")


def test_cli_main_measure_writes_a_traceable_run_log(tmp_path: Path) -> None:
    """Every CLI run must leave a timestamped .log next to its outputs so the
    user can rastrear errors after the console output is gone."""
    cfg, data, out = tmp_path / "c", tmp_path / "d", tmp_path / "o"
    for p in (cfg, data, out):
        p.mkdir()

    def _fake_run(**kwargs: object) -> int:
        logger.info("apuração da competência {}", kwargs["competencia"])
        logger.error("falha simulada no indicador X")
        return 1

    with patch("pyauditor.cli.main.run_measure", side_effect=_fake_run):
        code = cli_main(
            ["measure", "2026-06", "--config-dir", str(cfg), "--data-dir", str(data), "--output-dir", str(out)]
        )

    assert code == 1
    log_files = sorted((out / "2026-06").glob("pyauditor-measure-2026-06-*.log"))
    assert len(log_files) == 1
    content = log_files[0].read_text(encoding="utf-8")
    assert "apuração da competência 2026-06" in content
    assert "falha simulada no indicador X" in content


def test_cli_main_report_dispatches_with_output_filename(tmp_path: Path) -> None:
    capa_path = tmp_path / "capa.xlsx"
    roms_dir = tmp_path / "roms"
    out_dir = tmp_path / "reports"
    config_dir = tmp_path / "configs"
    with patch("pyauditor.cli.main.run_report", return_value=0) as m:
        code = cli_main(
            [
                "report",
                "2026-06",
                "--capa-path",
                str(capa_path),
                "--roms-dir",
                str(roms_dir),
                "--output-dir",
                str(out_dir),
                "--config-dir",
                str(config_dir),
            ]
        )
        assert code == 0
        assert m.call_args.kwargs["competencia"] == "2026-06"
        assert m.call_args.kwargs["capa_path"] == capa_path
        assert m.call_args.kwargs["roms_dir"] == roms_dir
        assert m.call_args.kwargs["output_path"] == out_dir / "relatorio_2026-06.xlsx"
        assert m.call_args.kwargs["config_dir"] == config_dir


def test_cli_main_unknown_exits_2() -> None:
    with pytest.raises(SystemExit) as e:
        cli_main(["unknown"])
    assert e.value.code == 2