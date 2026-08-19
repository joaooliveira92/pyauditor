from __future__ import annotations

import argparse
from pathlib import Path
from typing import assert_type
from unittest.mock import patch

import pytest

from pyauditor.cli.main import MeasureRequest, build_parser, cli_main


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


def test_cli_main_bootstrap_default_capa_path() -> None:
    with patch("pyauditor.cli.main.run_bootstrap", return_value=0) as m:
        code = cli_main(["bootstrap"])
        assert code == 0
        assert m.call_args.args[0] == Path("capa.xlsx")


def test_cli_main_report_dispatches_with_output_filename(tmp_path: Path) -> None:
    capa_path = tmp_path / "capa.xlsx"
    roms_dir = tmp_path / "roms"
    out_dir = tmp_path / "reports"
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
            ]
        )
        assert code == 0
        assert m.call_args.kwargs["competencia"] == "2026-06"
        assert m.call_args.kwargs["capa_path"] == capa_path
        assert m.call_args.kwargs["roms_dir"] == roms_dir
        assert m.call_args.kwargs["output_path"] == out_dir / "relatorio_2026-06.xlsx"


def test_cli_main_unknown_exits_2() -> None:
    with pytest.raises(SystemExit) as e:
        cli_main(["unknown"])
    assert e.value.code == 2