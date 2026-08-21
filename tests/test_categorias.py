from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from pyauditor.config.categorias import (
    CategoriaConfig,
    CategoriasFile,
    GrupoExecutorMode,
    WholeIndicatorMode,
    load_categorias,
)

_VALID_YAML = """
categorias:
  ATENDIMENTO_N1:
    label: "Atendimento Remoto aos Usuários"
    inms:
      "1.1": {mode: grupo_executor, in_values: ["(CIT/MINC) - 1º Nível"]}
      "1.11": {mode: whole_indicator}
  OPERACAO_N3:
    label: "Operação e Sustentação da Infraestrutura de TI"
    inms:
      "1.1": {mode: grupo_executor, catch_all_contains: "(CIT)"}
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "categorias.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_load_categorias_valid_schema(tmp_path: Path) -> None:
    load_categorias.cache_clear()
    path = _write(tmp_path, _VALID_YAML)

    result = load_categorias(path)

    assert isinstance(result, CategoriasFile)
    n1 = result.categorias["ATENDIMENTO_N1"]
    assert n1.label == "Atendimento Remoto aos Usuários"
    entry_11 = n1.inms["1.1"]
    assert isinstance(entry_11, GrupoExecutorMode)
    assert entry_11.in_values == ["(CIT/MINC) - 1º Nível"]
    assert entry_11.catch_all_contains is None
    entry_111 = n1.inms["1.11"]
    assert isinstance(entry_111, WholeIndicatorMode)

    n3 = result.categorias["OPERACAO_N3"]
    catch_all_entry = n3.inms["1.1"]
    assert isinstance(catch_all_entry, GrupoExecutorMode)
    assert catch_all_entry.catch_all_contains == "(CIT)"
    assert catch_all_entry.in_values is None


def test_load_categorias_unknown_mode_rejected(tmp_path: Path) -> None:
    load_categorias.cache_clear()
    path = _write(
        tmp_path,
        """
categorias:
  ATENDIMENTO_N1:
    label: "Atendimento Remoto aos Usuários"
    inms:
      "1.1": {mode: something_else}
""",
    )

    with pytest.raises(ValueError, match="invalid categorias file"):
        load_categorias(path)


def test_load_categorias_grupo_executor_both_filters_rejected(tmp_path: Path) -> None:
    load_categorias.cache_clear()
    path = _write(
        tmp_path,
        """
categorias:
  ATENDIMENTO_N1:
    label: "Atendimento Remoto aos Usuários"
    inms:
      "1.1": {mode: grupo_executor, in_values: ["a"], catch_all_contains: "(CIT)"}
""",
    )

    with pytest.raises(ValueError, match="exactly one of"):
        load_categorias(path)


def test_load_categorias_grupo_executor_no_filter_rejected(tmp_path: Path) -> None:
    load_categorias.cache_clear()
    path = _write(
        tmp_path,
        """
categorias:
  ATENDIMENTO_N1:
    label: "Atendimento Remoto aos Usuários"
    inms:
      "1.1": {mode: grupo_executor}
""",
    )

    with pytest.raises(ValueError, match="exactly one of"):
        load_categorias(path)


def test_load_categorias_malformed_yaml_raises_actionable_value_error(tmp_path: Path) -> None:
    load_categorias.cache_clear()
    path = _write(tmp_path, "categorias:\n  ATENDIMENTO_N1: [unclosed\n")

    with pytest.raises(ValueError, match="malformed YAML"):
        load_categorias(path)


def test_load_categorias_missing_categorias_key_raises(tmp_path: Path) -> None:
    load_categorias.cache_clear()
    path = _write(tmp_path, "not_categorias: {}\n")

    with pytest.raises(ValueError, match="invalid categorias file"):
        load_categorias(path)


def test_load_categorias_caches_by_path(tmp_path: Path) -> None:
    load_categorias.cache_clear()
    path = _write(tmp_path, _VALID_YAML)

    assert load_categorias(path) is load_categorias(path)


def test_categoria_rejects_empty_inms_map() -> None:
    with pytest.raises(ValidationError):
        CategoriaConfig(label="x", inms={})


def test_grupo_executor_mode_is_frozen() -> None:
    entry = GrupoExecutorMode(mode="grupo_executor", in_values=["a"])
    with pytest.raises(ValidationError):
        entry.in_values = ["b"]


@pytest.mark.parametrize("orgao", ["MinC", "MTur"])
def test_real_categorias_yaml_loads_and_covers_expected_inms(orgao: str) -> None:
    load_categorias.cache_clear()
    path = Path(__file__).parent.parent / "configs" / orgao / "categorias.yaml"

    result = load_categorias(path)

    assert set(result.categorias) == {
        "ATENDIMENTO_N1",
        "ATENDIMENTO_N2",
        "OPERACAO_N3",
        "MONITORAMENTO_NOC_SOC",
    }
    # 1.6 não tem Grupo_executor em nenhum dos dois órgãos (dataset SLA
    # pré-agregado): conta só em OPERACAO_N3, sem duplicar em N1/N2 (regra
    # de não-duplicação do ticket 02).
    n1 = result.categorias["ATENDIMENTO_N1"]
    assert set(n1.inms) == {"1.1", "1.2", "1.7", "1.11", "1.12", "1.13"}
    n2 = result.categorias["ATENDIMENTO_N2"]
    assert set(n2.inms) == {"1.1", "1.2", "1.7"}
    n3 = result.categorias["OPERACAO_N3"]
    assert set(n3.inms) == {"1.1", "1.2", "1.3", "1.6", "1.7", "1.9", "1.14"}
    noc_soc = result.categorias["MONITORAMENTO_NOC_SOC"]
    assert set(noc_soc.inms) == {"1.4", "1.5", "1.14"}
    for categoria in result.categorias.values():
        assert "1.8" not in categoria.inms
        assert "1.10" not in categoria.inms


def test_minc_1_6_is_whole_indicator_only_in_operacao_n3() -> None:
    load_categorias.cache_clear()
    path = Path(__file__).parent.parent / "configs" / "MinC" / "categorias.yaml"

    result = load_categorias(path)

    assert "1.6" not in result.categorias["ATENDIMENTO_N1"].inms
    assert "1.6" not in result.categorias["ATENDIMENTO_N2"].inms
    entry = result.categorias["OPERACAO_N3"].inms["1.6"]
    assert isinstance(entry, WholeIndicatorMode)


def test_mtur_1_6_is_whole_indicator_only_in_operacao_n3() -> None:
    load_categorias.cache_clear()
    path = Path(__file__).parent.parent / "configs" / "MTur" / "categorias.yaml"

    result = load_categorias(path)

    assert "1.6" not in result.categorias["ATENDIMENTO_N1"].inms
    assert "1.6" not in result.categorias["ATENDIMENTO_N2"].inms
    entry = result.categorias["OPERACAO_N3"].inms["1.6"]
    assert isinstance(entry, WholeIndicatorMode)
