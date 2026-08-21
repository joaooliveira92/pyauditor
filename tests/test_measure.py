from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pyauditor.cli.measure import run_measure


def _cfg(id_: str, contractual: str) -> SimpleNamespace:
    return SimpleNamespace(indicator=SimpleNamespace(id=id_, contractual_id=contractual))


def _loaded(id_: str, contractual: str) -> tuple[Path, str, SimpleNamespace]:
    return Path(f"{id_}.yaml"), "deadbeef", _cfg(id_, contractual)


def test_happy_path(tmp_path: Path) -> None:
    cfg_dir = tmp_path / "configs"
    cfg_dir.mkdir()
    data_dir = tmp_path / "input"
    data_dir.mkdir()
    out_dir = tmp_path / "roms"
    out_dir.mkdir()
    configs = [_loaded("ind_a", "C-A"), _loaded("ind_b", "C-B")]
    result_ok = SimpleNamespace(hard_failure=False)
    result_fail = SimpleNamespace(hard_failure=True)

    with patch("pyauditor.cli.measure.discover_config_files", return_value=configs), \
         patch("pyauditor.cli.measure.measure", side_effect=[result_ok, result_fail]), \
         patch("pyauditor.cli.measure.render_rom", return_value="# ROM"), \
         patch("pyauditor.cli.measure.summarize", return_value=SimpleNamespace(to_dict=lambda: {})):
        code = run_measure("2026-06", cfg_dir, data_dir, out_dir)
        assert code.status == "error"  # one hard_failure
        assert (out_dir / "2026-06" / "ind_a.md").read_text(encoding="utf-8") == "# ROM"
        assert (out_dir / "2026-06" / "ind_b.md").exists()
        assert (out_dir / "2026-06" / "ind_a.json").exists()

def test_no_configs_returns_1(tmp_path: Path) -> None:
    with patch("pyauditor.cli.measure.discover_config_files", return_value=[]):
        assert run_measure("2026-06", tmp_path, tmp_path, tmp_path).status == "error"

def test_invalid_competencia_rejected(tmp_path: Path) -> None:
    assert run_measure("2026/06", tmp_path, tmp_path, tmp_path).status == "error"
    assert run_measure("../../etc", tmp_path, tmp_path, tmp_path).status == "error"
    assert run_measure("2026-13-extra", tmp_path, tmp_path, tmp_path).status == "error"

def test_sanitize_id_prevents_traversal(tmp_path: Path) -> None:
    loaded = [_loaded("../../evil", "C-EVIL")]
    with patch("pyauditor.cli.measure.discover_config_files", return_value=loaded), \
         patch("pyauditor.cli.measure.measure", return_value=SimpleNamespace(hard_failure=False)), \
         patch("pyauditor.cli.measure.render_rom", return_value="x"), \
         patch("pyauditor.cli.measure.summarize", return_value=SimpleNamespace(to_dict=lambda: {})):
        code = run_measure("2026-06", tmp_path, tmp_path, tmp_path)
        assert code.status == "done"
        # sanitized, not traversing
        assert (tmp_path / "2026-06" / "evil.md").exists()
        assert not (tmp_path / "evil.md").exists()

def test_mkdir_oserror_returns_1(tmp_path: Path) -> None:
    loaded = [_loaded("a", "C-A")]
    with patch("pyauditor.cli.measure.discover_config_files", return_value=loaded), \
         patch.object(Path, "mkdir", side_effect=OSError("ro")):
        assert run_measure("2026-06", tmp_path, tmp_path, tmp_path).status == "error"

def test_write_oserror_marks_hard_failure(tmp_path: Path) -> None:
    loaded = [_loaded("a", "C-A")]
    with patch("pyauditor.cli.measure.discover_config_files", return_value=loaded), \
         patch("pyauditor.cli.measure.measure", return_value=SimpleNamespace(hard_failure=False)), \
         patch("pyauditor.cli.measure.render_rom", return_value="x"), \
         patch.object(Path, "write_text", side_effect=OSError("disk full")):
        assert run_measure("2026-06", tmp_path, tmp_path, tmp_path).status == "error"

def test_measure_exception_continues(tmp_path: Path) -> None:
    loaded = [_loaded("a", "C-A"), _loaded("b", "C-B")]
    with patch("pyauditor.cli.measure.discover_config_files", return_value=loaded), \
         patch("pyauditor.cli.measure.measure", side_effect=RuntimeError("boom")), \
         patch("pyauditor.cli.measure.render_rom", return_value="x"):
        assert run_measure("2026-06", tmp_path, tmp_path, tmp_path).status == "error"

def test_missing_equipe_warns_but_does_not_fail(tmp_path: Path) -> None:
    """Responsáveis são informativos — diferente do valor-base do `report`,
    equipe.csv ausente nunca bloqueia `measure` (warning + '[a preencher]')."""
    loaded = [_loaded("a", "C-A")]
    missing_equipe = tmp_path / "equipe.csv"
    with patch("pyauditor.cli.measure.discover_config_files", return_value=loaded), \
         patch("pyauditor.cli.measure.measure", return_value=SimpleNamespace(hard_failure=False)), \
         patch("pyauditor.cli.measure.render_rom", return_value="x") as render_mock, \
         patch("pyauditor.cli.measure.summarize", return_value=SimpleNamespace(to_dict=lambda: {})):
        code = run_measure(
            "2026-06", tmp_path, tmp_path, tmp_path, equipe_path=missing_equipe
        )
        assert code.status == "done"
        assert render_mock.call_args.kwargs["capa_fields"] == {}
        assert any("equipe não encontrada" in w for w in code.warnings)


def test_equipe_missing_fields_warn_once_per_run(tmp_path: Path) -> None:
    loaded = [_loaded("a", "C-A"), _loaded("b", "C-B")]
    equipe_path = tmp_path / "equipe.csv"
    equipe_path.write_text(
        "FUNÇÃO,NOME,SIAPE\nFiscal técnico,Fulano de Tal,1234567\n",
        encoding="utf-8-sig",
    )
    with (
        patch("pyauditor.cli.measure.discover_config_files", return_value=loaded),
        patch("pyauditor.cli.measure.measure", return_value=SimpleNamespace(hard_failure=False)),
        patch("pyauditor.cli.measure.render_rom", return_value="x"),
        patch("pyauditor.cli.measure.summarize", return_value=SimpleNamespace(to_dict=lambda: {})),
        patch("pyauditor.cli.measure.logger") as logger_mock,
    ):
        code = run_measure("2026-06", tmp_path, tmp_path, tmp_path, equipe_path=equipe_path)
        assert code.status == "done"
        warnings = [call.args[0] for call in logger_mock.warning.call_args_list]
        resumo = [w for w in warnings if "sem preencher" in w]
        assert len(resumo) == 1  # o resumo agregado é uma vez por execução
        assert "Fiscal requisitante" in resumo[0]
        assert "Fiscal técnico" not in resumo[0]  # esse foi preenchido


def test_equipe_fields_reach_render_rom_and_malformed_degrades(tmp_path: Path) -> None:
    loaded = [_loaded("a", "C-A")]
    summarize_result = SimpleNamespace(to_dict=lambda: {})
    equipe_path = tmp_path / "equipe.csv"

    equipe_path.write_text(
        "FUNÇÃO,NOME,SIAPE\nGestor do Contrato,Beltrano,7654321\n",
        encoding="utf-8-sig",
    )
    with patch("pyauditor.cli.measure.discover_config_files", return_value=loaded), \
         patch("pyauditor.cli.measure.measure", return_value=SimpleNamespace(hard_failure=False)), \
         patch("pyauditor.cli.measure.render_rom", return_value="x") as render_mock, \
         patch("pyauditor.cli.measure.summarize", return_value=summarize_result):
        code = run_measure("2026-06", tmp_path, tmp_path, tmp_path, equipe_path=equipe_path)
        assert code.status == "done"
        # normalização de caixa/acento mapeia no rótulo canônico
        assert render_mock.call_args.kwargs["capa_fields"] == {
            "Gestor do contrato": "Beltrano (7654321)"
        }

    equipe_path.write_text("cabecalho,errado\n", encoding="utf-8-sig")
    with patch("pyauditor.cli.measure.discover_config_files", return_value=loaded), \
         patch("pyauditor.cli.measure.measure", return_value=SimpleNamespace(hard_failure=False)), \
         patch("pyauditor.cli.measure.render_rom", return_value="x") as render_mock, \
         patch("pyauditor.cli.measure.summarize", return_value=summarize_result):
        code = run_measure("2026-06", tmp_path, tmp_path, tmp_path, equipe_path=equipe_path)
        assert code.status == "done"  # malformado é dado incompleto, não falha
        assert render_mock.call_args.kwargs["capa_fields"] == {}
        assert any("falha ao ler" in w for w in code.warnings)
