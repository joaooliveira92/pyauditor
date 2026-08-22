import pytest

from pyauditor.excel.glosas import (
    Historico,
    competencia_anterior,
    compute_glosa,
    historico_entry,
    houve_reincidencia,
    janela_reincidencia,
    saldo_anterior_pct_de,
)


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
    assert result.valor_da_glosa == pytest.approx(
        30_000.0
    )  # 30% de 100.000, não 40%
    assert result.saldo_rolado_pct == pytest.approx(10.0)


def test_glosa_above_cap_in_final_month_does_not_roll_over() -> None:
    result = compute_glosa(
        total_points=40_000.0, valor_base=100_000.0, is_final_month=True
    )

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


def test_glosa_consumes_saldo_anterior() -> None:
    # 20000 pontos * 0.001% = 20%, + 15 p.p. rolados do mês anterior = 35% ->
    # capped at 30%, 5 p.p. de novo excedente
    result = compute_glosa(
        total_points=20_000.0, valor_base=100_000.0, saldo_anterior_pct=15.0
    )

    assert result.raw_pct == pytest.approx(35.0)
    assert result.percentual_ajuste == pytest.approx(30.0)
    assert result.teto_atingido is True
    assert result.saldo_rolado_pct == pytest.approx(5.0)


def test_glosa_raw_pct_matches_percentual_plus_saldo_rolado() -> None:
    result = compute_glosa(total_points=40_000.0, valor_base=100_000.0)

    assert result.raw_pct == pytest.approx(
        result.percentual_ajuste + result.saldo_rolado_pct
    )


def test_competencia_anterior_rolls_year_boundary() -> None:
    assert competencia_anterior('2026-01') == '2025-12'
    assert competencia_anterior('2026-07') == '2026-06'


def test_janela_reincidencia_six_months_ending_at_competencia() -> None:
    assert janela_reincidencia('2026-06') == [
        '2026-06',
        '2026-05',
        '2026-04',
        '2026-03',
        '2026-02',
        '2026-01',
    ]


def test_saldo_anterior_pct_de_no_history() -> None:
    assert saldo_anterior_pct_de({}, '2026-06') == 0.0


def test_saldo_anterior_pct_de_reads_prior_month() -> None:
    historico: Historico = {'2026-05': {'saldo_rolado_pct': 7.5}}

    assert saldo_anterior_pct_de(historico, '2026-06') == pytest.approx(7.5)


def test_houve_reincidencia_below_threshold() -> None:
    historico: Historico = {
        '2026-04': {'teto_atingido': True},
        '2026-05': {'teto_atingido': False},
    }

    assert (
        houve_reincidencia(historico, '2026-06', teto_atingido_mes_atual=True)
        is False
    )


def test_houve_reincidencia_three_times_in_six_months() -> None:
    historico: Historico = {
        '2026-04': {'teto_atingido': True},
        '2026-05': {'teto_atingido': True},
    }

    assert (
        houve_reincidencia(historico, '2026-06', teto_atingido_mes_atual=True)
        is True
    )


def test_houve_reincidencia_ignores_occurrences_outside_window() -> None:
    historico: Historico = {
        '2025-12': {
            'teto_atingido': True
        },  # 7 meses antes de 2026-06, fora da janela
        '2026-04': {'teto_atingido': True},
    }

    assert (
        houve_reincidencia(historico, '2026-06', teto_atingido_mes_atual=True)
        is False
    )


def test_historico_entry_shape() -> None:
    glosa = compute_glosa(total_points=40_000.0, valor_base=100_000.0)

    entry = historico_entry('2026-06', glosa)

    assert entry == {
        'total_points': 40_000.0,
        'raw_pct': pytest.approx(40.0),
        'percentual_ajuste': pytest.approx(30.0),
        'teto_atingido': True,
        'saldo_rolado_pct': pytest.approx(10.0),
    }
