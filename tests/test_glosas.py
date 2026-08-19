import pytest

from pyauditor.excel.glosas import compute_glosa


def test_glosa_below_cap() -> None:
    # 1000 pontos * 0.001% = 1% de ajuste, dentro do teto de 30%
    result = compute_glosa(total_points=1000.0, valor_base=100_000.0)

    assert result.percentual_ajuste == pytest.approx(1.0)
    assert result.teto_atingido is False
    assert result.valor_da_glosa == pytest.approx(1000.0)  # 1% de 100.000
    assert result.saldo_rolado_pct == 0.0


def test_glosa_exactly_at_cap() -> None:
    # 30000 pontos * 0.001% = 30% — no teto, sem excedente
    result = compute_glosa(total_points=30_000.0, valor_base=100_000.0)

    assert result.percentual_ajuste == pytest.approx(30.0)
    assert result.teto_atingido is False
    assert result.saldo_rolado_pct == 0.0


def test_glosa_above_cap_rolls_over() -> None:
    # 40000 pontos * 0.001% = 40% -> capped at 30%, 10 p.p. de excedente
    result = compute_glosa(total_points=40_000.0, valor_base=100_000.0)

    assert result.percentual_ajuste == pytest.approx(30.0)
    assert result.teto_atingido is True
    assert result.valor_da_glosa == pytest.approx(30_000.0)  # 30% de 100.000, não 40%
    assert result.saldo_rolado_pct == pytest.approx(10.0)


def test_glosa_above_cap_in_final_month_does_not_roll_over() -> None:
    result = compute_glosa(total_points=40_000.0, valor_base=100_000.0, is_final_month=True)

    assert result.percentual_ajuste == pytest.approx(30.0)
    assert result.teto_atingido is True
    assert result.saldo_rolado_pct == 0.0  # no next month to roll to


def test_glosa_without_valor_base_still_computes_percentual() -> None:
    result = compute_glosa(total_points=1000.0, valor_base=None)

    assert result.percentual_ajuste == pytest.approx(1.0)
    assert result.valor_da_glosa is None


def test_glosa_zero_points() -> None:
    result = compute_glosa(total_points=0.0, valor_base=100_000.0)

    assert result.percentual_ajuste == pytest.approx(0.0)
    assert result.teto_atingido is False
    assert result.valor_da_glosa == pytest.approx(0.0)
