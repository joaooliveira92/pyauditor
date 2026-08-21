from pathlib import Path
from unittest.mock import patch

from pyauditor.cli.bootstrap import run_bootstrap


def test_run_bootstrap_creates_common_and_orgao_capas(tmp_path: Path) -> None:
    orgao_capa = tmp_path / "capa_MinC.csv"

    result = run_bootstrap(orgao_capa, "MinC")

    assert result.status == "done"
    assert result.created is True
    assert orgao_capa.exists()
    assert (tmp_path / "capa.csv").exists()


def test_run_bootstrap_is_a_noop_when_capas_exist(tmp_path: Path) -> None:
    orgao_capa = tmp_path / "capa_MinC.csv"
    run_bootstrap(orgao_capa, "MinC")
    comum = tmp_path / "capa.csv"
    mtime_orgao = orgao_capa.stat().st_mtime_ns
    mtime_comum = comum.stat().st_mtime_ns

    result = run_bootstrap(orgao_capa, "MinC")

    assert result.status == "done"
    assert result.created is False
    assert orgao_capa.stat().st_mtime_ns == mtime_orgao
    assert comum.stat().st_mtime_ns == mtime_comum


def test_run_bootstrap_converts_unexpected_exception_to_error_result(tmp_path: Path) -> None:
    orgao_capa = tmp_path / "capa_MinC.csv"

    with patch("pyauditor.cli.bootstrap.bootstrap_capa_csv", side_effect=ValueError("boom")):
        result = run_bootstrap(orgao_capa, "MinC")

    assert result.status == "error"
    assert result.error_message is not None
    assert "boom" in result.error_message


def test_run_bootstrap_os_error_message_has_actionable_hint(tmp_path: Path) -> None:
    # Ticket 11: PermissionError/lock não têm como ser distinguidos de forma
    # confiável a partir da OSError, então a dica cobre as duas causas.
    orgao_capa = tmp_path / "capa_MinC.csv"

    with patch(
        "pyauditor.cli.bootstrap.bootstrap_capa_csv",
        side_effect=PermissionError("Permission denied"),
    ):
        result = run_bootstrap(orgao_capa, "MinC")

    assert result.status == "error"
    assert result.error_message is not None
    assert "permiss" in result.error_message.lower()
    assert "aberto em outro programa" in result.error_message


# Spec competencia-cli-equipe §6/§7 — bootstrap também cria o esqueleto de
# equipe.csv, fonte única dos responsáveis.


def test_run_bootstrap_cria_esqueleto_equipe_csv(tmp_path: Path) -> None:
    orgao_capa = tmp_path / "capa_MinC.csv"

    result = run_bootstrap(orgao_capa, "MinC")

    assert result.status == "done"
    equipe = tmp_path / "equipe.csv"
    assert equipe.exists()
    linhas = equipe.read_text(encoding="utf-8-sig").splitlines()
    assert linhas[0] == "FUNÇÃO,NOME,SIAPE"
    funcoes = [linha.split(",")[0] for linha in linhas[1:]]
    titulares = [f for f in funcoes if not f.endswith(" - Substituto")]
    substitutos = [f for f in funcoes if f.endswith(" - Substituto")]
    assert len(titulares) == 4
    assert len(substitutos) == 4
    # Esqueleto hand-fill: nomes e siapes vazios.
    assert all(linha.split(",")[1:] == ["", ""] for linha in linhas[1:])


def test_run_bootstrap_nunca_toca_equipe_existente(tmp_path: Path) -> None:
    orgao_capa = tmp_path / "capa_MinC.csv"
    equipe = tmp_path / "equipe.csv"
    equipe.write_text("FUNÇÃO,NOME,SIAPE\nGestor Contratual,Maria,123\n", encoding="utf-8")

    result = run_bootstrap(orgao_capa, "MinC")
    segunda = run_bootstrap(orgao_capa, "MinC")

    assert result.status == "done"
    assert segunda.status == "done"
    assert (
        equipe.read_text(encoding="utf-8")
        == "FUNÇÃO,NOME,SIAPE\nGestor Contratual,Maria,123\n"
    )