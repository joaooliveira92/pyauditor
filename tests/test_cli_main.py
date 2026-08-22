from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import assert_type
from unittest.mock import patch

import pytest

from pyauditor.cli.main import (
    MeasureRequest,
    _dispatch_bootstrap,
    _dispatch_consolidate,
    _dispatch_measure,
    build_parser,
    cli_main,
)
from pyauditor.logging import logger
from pyauditor.periodo import PeriodoAfericao


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
        manifest_path=Path("configs") / "MinC" / "datasets.yaml",
        orgao="MinC",
        strict=False,
    )
    assert_type(r.competencia, str)
    with pytest.raises(AttributeError):
        r.competencia = "2026-07"  # type: ignore[misc]  # frozen


def test_cli_main_happy_path(tmp_path: Path) -> None:
    cfg, data, out = tmp_path / "c", tmp_path / "d", tmp_path / "o"
    for p in (cfg, data, out):
        p.mkdir()
    with patch("pyauditor.cli.main.run_measure", return_value=SimpleNamespace(status="done")) as m:
        code = cli_main(
            [
                "measure",
                "2026-06",
                "--config-dir",
                str(cfg),
                "--data-dir",
                str(data),
                "--output-dir",
                str(out),
            ]
        )
        assert code == 0
        assert m.call_args.kwargs["competencia"] == "2026-06"
        assert m.call_args.kwargs["config_dir"] == cfg / "MinC"
        assert m.call_args.kwargs["expected_orgao"] == "MinC"


def test_cli_main_split_dispatches(tmp_path: Path) -> None:
    cfg, data = tmp_path / "c", tmp_path / "d"
    for p in (cfg, data):
        p.mkdir()
    with patch("pyauditor.cli.main.run_split", return_value=SimpleNamespace(status="done")) as m:
        code = cli_main(["split", "2026-06", "--config-dir", str(cfg), "--data-dir", str(data)])
        assert code == 0
        assert m.call_args.kwargs["competencia"] == "2026-06"
        assert m.call_args.kwargs["config_dir"] == cfg / "MinC"
        assert m.call_args.kwargs["expected_orgao"] == "MinC"


def test_cli_main_measure_dispatch_passes_equipe_periodo_strict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§2/§6 — o despachante deriva a janela da competência, resolve
    `equipe.csv` na raiz de --data-dir e repassa `--strict`."""
    monkeypatch.chdir(tmp_path)
    cfg, data, out = tmp_path / "c", tmp_path / "d", tmp_path / "o"
    for p in (cfg, data, out):
        p.mkdir()
    with patch("pyauditor.cli.main.run_measure", return_value=SimpleNamespace(status="done")) as m:
        code = cli_main(
            [
                "measure",
                "2026-06",
                "--config-dir",
                str(cfg),
                "--data-dir",
                str(data),
                "--output-dir",
                str(out),
            ]
        )
        assert code == 0
        assert m.call_args.kwargs["equipe_path"] == data / "equipe.csv"
        assert m.call_args.kwargs["periodo"] == PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))
        assert m.call_args.kwargs["strict"] is False


def test_cli_main_measure_dispatch_strict_flag(tmp_path: Path) -> None:
    cfg, data, out = tmp_path / "c", tmp_path / "d", tmp_path / "o"
    for p in (cfg, data, out):
        p.mkdir()
    with patch("pyauditor.cli.main.run_measure", return_value=SimpleNamespace(status="done")) as m:
        code = cli_main(
            [
                "measure",
                "2026-06",
                "--config-dir",
                str(cfg),
                "--data-dir",
                str(data),
                "--output-dir",
                str(out),
                "--strict",
            ]
        )
        assert code == 0
        assert m.call_args.kwargs["strict"] is True


def test_cli_main_bootstrap_dispatches_with_capa_path(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    capa_path = data_dir / "capa.csv"
    with patch(
        "pyauditor.cli.main.run_bootstrap", return_value=SimpleNamespace(status="done")
    ) as m:
        code = cli_main(["bootstrap", "--data-dir", str(data_dir), "--capa-path", str(capa_path)])
        assert code == 0
        assert m.call_args.args[0] == capa_path.parent / "capa_MinC.csv"


def test_cli_main_bootstrap_default_capa_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    with patch(
        "pyauditor.cli.main.run_bootstrap", return_value=SimpleNamespace(status="done")
    ) as m:
        code = cli_main(["bootstrap"])
        assert code == 0
        assert m.call_args.args[0] == Path("input/capa_MinC.csv")


def test_cli_main_measure_writes_a_traceable_run_log(tmp_path: Path) -> None:
    """Every CLI run must leave a timestamped .log next to its outputs so the
    user can rastrear errors after the console output is gone."""
    cfg, data, out = tmp_path / "c", tmp_path / "d", tmp_path / "o"
    for p in (cfg, data, out):
        p.mkdir()

    def _fake_run(**kwargs: object) -> SimpleNamespace:
        logger.info("apuração da competência {}", kwargs["competencia"])
        logger.error("falha simulada no indicador X")
        return SimpleNamespace(status="error")

    with patch("pyauditor.cli.main.run_measure", side_effect=_fake_run):
        code = cli_main(
            [
                "measure",
                "2026-06",
                "--config-dir",
                str(cfg),
                "--data-dir",
                str(data),
                "--output-dir",
                str(out),
            ]
        )

    assert code == 1
    log_files = sorted((out / "MinC" / "2026-06").glob("pyauditor-measure-2026-06-*.log"))
    assert len(log_files) == 1
    content = log_files[0].read_text(encoding="utf-8")
    assert "apuração da competência 2026-06" in content
    assert "falha simulada no indicador X" in content


def test_cli_main_measure_resolves_shared_manifest_when_both_exist(tmp_path: Path) -> None:
    """Issue 01 — fonte única: com `datasets.yaml` em `_shared` e no per-órgão,
    o `measure` (assim como o `run`) usa o manifest de `_shared`."""
    cfg, data, out = tmp_path / "c", tmp_path / "d", tmp_path / "o"
    for p in (cfg, data, out):
        p.mkdir()
    (cfg / "_shared").mkdir()
    (cfg / "MinC").mkdir()
    (cfg / "_shared" / "datasets.yaml").write_text(
        "datasets:\n  telefonemas:\n    file: tel.csv\n    delimiter: ';'\n", encoding="utf-8"
    )
    (cfg / "MinC" / "datasets.yaml").write_text(
        "datasets:\n  telefonemas:\n    file: tel.csv\n    delimiter: ','\n", encoding="utf-8"
    )
    with patch("pyauditor.cli.main.run_measure", return_value=SimpleNamespace(status="done")) as m:
        code = cli_main(
            [
                "measure",
                "2026-06",
                "--config-dir",
                str(cfg),
                "--data-dir",
                str(data),
                "--output-dir",
                str(out),
            ]
        )
        assert code == 0
        manifest = m.call_args.kwargs["manifest"]
        assert manifest is not None
        assert manifest.resolve("telefonemas").delimiter == ";"


def test_cli_main_report_dispatches_with_output_filename(tmp_path: Path) -> None:
    capa_path = tmp_path / "capa.xlsx"
    roms_dir = tmp_path / "roms"
    out_dir = tmp_path / "reports"
    config_dir = tmp_path / "configs"
    with (
        patch("pyauditor.cli.main.run_report", return_value=SimpleNamespace(status="done")) as m,
    ):
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
        assert m.call_args.kwargs["roms_dir"] == roms_dir / "MinC"
        assert m.call_args.kwargs["output_path"] == out_dir / "relatorio_2026-06_MinC.xlsx"
        assert m.call_args.kwargs["config_dir"] == config_dir / "MinC"


def test_cli_main_unknown_exits_2() -> None:
    with pytest.raises(SystemExit) as e:
        cli_main(["unknown"])
    assert e.value.code == 2


def test_cli_main_run_dispatches_to_run_run(tmp_path: Path) -> None:
    cfg, data, out, reports = (tmp_path / "c", tmp_path / "d", tmp_path / "o", tmp_path / "r")
    for p in (cfg, data, out, reports):
        p.mkdir()
    with patch("pyauditor.cli.main.run_run", return_value=0) as m:
        code = cli_main(
            [
                "run",
                "2026-06",
                "--config-dir",
                str(cfg),
                "--data-dir",
                str(data),
                "--output-dir",
                str(out),
                "--report-dir",
                str(reports),
            ]
        )
        assert code == 0
        assert m.call_args.kwargs["competencia"] == "2026-06"
        assert m.call_args.kwargs["orgao"] == "MinC"
        assert m.call_args.kwargs["config_dir"] == cfg
        assert m.call_args.kwargs["report_dir"] == reports


def test_dispatch_measure_is_callable_directly_without_argparse(tmp_path: Path) -> None:
    """The point of splitting cli_main's branches into _dispatch_* functions:
    each is independently testable with a hand-built Namespace, no argparse
    or the no-args guided-flow branch in the way."""
    cfg, data, out = tmp_path / "c", tmp_path / "d", tmp_path / "o"
    for p in (cfg, data, out):
        p.mkdir()
    args = build_parser().parse_args(
        [
            "measure",
            "2026-06",
            "--config-dir",
            str(cfg),
            "--data-dir",
            str(data),
            "--output-dir",
            str(out),
        ]
    )
    with patch("pyauditor.cli.main.run_measure", return_value=SimpleNamespace(status="done")) as m:
        code = _dispatch_measure(args)
        assert code == 0
        assert m.call_args.kwargs["competencia"] == "2026-06"


def test_dispatch_bootstrap_is_callable_directly_without_argparse(tmp_path: Path) -> None:
    capa_path = tmp_path / "capa.csv"
    args = build_parser().parse_args(["bootstrap", "--capa-path", str(capa_path)])
    with patch(
        "pyauditor.cli.main.run_bootstrap", return_value=SimpleNamespace(status="done")
    ) as m:
        code = _dispatch_bootstrap(args)
        assert code == 0
        assert m.call_args.args[0] == capa_path.parent / "capa_MinC.csv"


def test_cli_main_consolidate_final_month_reaches_run_consolidate(tmp_path: Path) -> None:
    """Ticket 10 — `consolidate --final-month` percola o parser até
    `run_consolidate(is_final_month=True)`: no mês final, `consolidado.xlsx`
    e `report.xlsx` desligam o rollover de glosa do mesmo jeito."""
    report_dir = tmp_path / "reports"
    roms_dir = tmp_path / "roms"
    data_dir = tmp_path / "input"
    for p in (report_dir, roms_dir, data_dir):
        p.mkdir()
    args = build_parser().parse_args(
        [
            "consolidate",
            "2026-06",
            "--report-dir",
            str(report_dir),
            "--roms-dir",
            str(roms_dir),
            "--data-dir",
            str(data_dir),
            "--final-month",
        ]
    )
    with patch(
        "pyauditor.cli.main.run_consolidate",
        return_value=SimpleNamespace(status="done"),
    ) as m:
        code = _dispatch_consolidate(args)
        assert code == 0
        assert m.call_args.kwargs["is_final_month"] is True


def test_cli_main_no_args_without_tty_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    code = cli_main([])
    assert code == 2


def test_cli_main_no_args_with_tty_runs_interactive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    with patch("pyauditor.interactive.run_interactive", return_value=0) as m:
        code = cli_main([])
        assert code == 0
        m.assert_called_once()
