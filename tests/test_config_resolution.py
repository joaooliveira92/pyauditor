"""Resolver único de config_dir + manifest (issue 01).

Precedência documentada e única: `_shared` vence quando existe (ADR 0003),
per-órgão é fallback. `cli/main.py` e `orchestration/run.py` usam este
módulo para que `measure` e `run` cheguem ao mesmo config_dir e ao mesmo
`DatasetManifest` para o mesmo órgão+base.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pyauditor.config.resolution import (
    load_manifest_for,
    resolve_config_dir,
    resolve_manifest_path,
)

_ORG = "MinC"


def test_resolve_config_dir_prefers_shared_when_dir_exists(tmp_path: Path) -> None:
    (tmp_path / "_shared").mkdir()
    (tmp_path / _ORG).mkdir()

    assert resolve_config_dir(tmp_path, _ORG) == tmp_path / "_shared"


def test_resolve_config_dir_falls_back_to_orgao_without_shared(tmp_path: Path) -> None:
    (tmp_path / _ORG).mkdir()

    assert resolve_config_dir(tmp_path, _ORG) == tmp_path / _ORG


def test_resolve_manifest_path_prefers_shared_when_both_exist(tmp_path: Path) -> None:
    (tmp_path / "_shared").mkdir()
    (tmp_path / _ORG).mkdir()
    (tmp_path / "_shared" / "datasets.yaml").write_text("datasets: {}\n", encoding="utf-8")
    (tmp_path / _ORG / "datasets.yaml").write_text("datasets: {}\n", encoding="utf-8")

    assert resolve_manifest_path(tmp_path, _ORG) == tmp_path / "_shared" / "datasets.yaml"


def test_resolve_manifest_path_falls_back_to_orgao_without_shared(tmp_path: Path) -> None:
    (tmp_path / _ORG).mkdir()
    (tmp_path / _ORG / "datasets.yaml").write_text("datasets: {}\n", encoding="utf-8")

    assert resolve_manifest_path(tmp_path, _ORG) == tmp_path / _ORG / "datasets.yaml"


def test_load_manifest_for_uses_shared_manifest_when_both_exist(tmp_path: Path) -> None:
    """A divergência de precedência (main `_shared`, run per-órgão) some: com
    `datasets.yaml` nos dois lugares, o manifest carregado é o de `_shared`."""
    (tmp_path / "_shared").mkdir()
    (tmp_path / _ORG).mkdir()
    (tmp_path / "_shared" / "datasets.yaml").write_text(
        "datasets:\n  telefonemas:\n    file: tel.csv\n    delimiter: ';'\n", encoding="utf-8"
    )
    (tmp_path / _ORG / "datasets.yaml").write_text(
        "datasets:\n  telefonemas:\n    file: tel.csv\n    delimiter: ','\n", encoding="utf-8"
    )

    manifest = load_manifest_for(tmp_path, _ORG)

    assert manifest is not None
    assert manifest.resolve("telefonemas").delimiter == ";"


def test_load_manifest_for_returns_none_when_no_manifest(tmp_path: Path) -> None:
    (tmp_path / _ORG).mkdir()

    assert load_manifest_for(tmp_path, _ORG) is None


def test_load_manifest_for_requires_manifest_in_resolved_config_dir(tmp_path: Path) -> None:
    """Fonte única: com `_shared` presente (diretório de config canônico), um
    `datasets.yaml` per-órgão não é consultado — sem configs de um diretório e
    delimiters de outro para o mesmo órgão+base."""
    (tmp_path / "_shared").mkdir()
    (tmp_path / _ORG).mkdir()
    (tmp_path / _ORG / "datasets.yaml").write_text(
        "datasets:\n  telefonemas:\n    file: tel.csv\n    delimiter: ','\n", encoding="utf-8"
    )

    assert load_manifest_for(tmp_path, _ORG) is None


def test_measure_and_run_resolve_the_same_manifest_for_same_orgao_base(
    tmp_path: Path,
) -> None:
    """Issue 01 — para o mesmo órgão+base, `measure` (main) e `run` chegam ao
    mesmo config_dir e ao mesmo `DatasetManifest`."""
    from pyauditor.cli.main import cli_main
    from pyauditor.orchestration.run import RunRequest, execute_run

    base = tmp_path / "configs"
    data = tmp_path / "input"
    for d in (base / "_shared", base / _ORG, data):
        d.mkdir(parents=True)
    (base / "_shared" / "datasets.yaml").write_text(
        "datasets:\n  telefonemas:\n    file: tel.csv\n    delimiter: ';'\n", encoding="utf-8"
    )
    (base / _ORG / "datasets.yaml").write_text(
        "datasets:\n  telefonemas:\n    file: tel.csv\n    delimiter: ','\n", encoding="utf-8"
    )

    with patch(
        "pyauditor.cli.main.run_measure", return_value=SimpleNamespace(status="done")
    ) as m_main:
        code = cli_main(
            [
                "measure",
                "2026-06",
                "--config-dir",
                str(base),
                "--data-dir",
                str(data),
                "--output-dir",
                str(tmp_path / "roms"),
            ]
        )
        assert code == 0
    main_config_dir = m_main.call_args.kwargs["config_dir"]
    main_manifest = m_main.call_args.kwargs["manifest"]

    request = RunRequest(
        competencia="2026-06",
        orgao=_ORG,
        config_dir=base,
        data_dir=data,
        output_dir=tmp_path / "roms",
        report_dir=tmp_path / "reports",
        capa_path=data / "capa.csv",
        runs_dir=tmp_path / ".pyauditor" / "runs",
        commands=frozenset({"measure"}),
    )
    with patch(
        "pyauditor.orchestration.run.run_measure",
        return_value=SimpleNamespace(status="done", error_message=None),
    ) as m_run:
        execute_run(request)
    run_config_dir = m_run.call_args.kwargs["config_dir"]
    run_manifest = m_run.call_args.kwargs["manifest"]

    assert main_config_dir == run_config_dir == base / "_shared"
    assert main_manifest is not None
    assert run_manifest is not None
    assert main_manifest.resolve("telefonemas").delimiter == ";"
    assert run_manifest.resolve("telefonemas").delimiter == ";"
