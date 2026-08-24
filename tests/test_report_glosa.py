"""Unidade de `excel/report.py:compute_report_glosa` (ticket 01 rede-testes):
a glosa do relatório por órgão travada como função pura, sem workbook —
pronta para a extração do ticket 04 (`excel/report/_glosa.py`).

Cobre soma de pontos, teto/rollover, consumo do saldo rolado, ausência de
`valor_base` e a exclusão de sumários base quando existem categorias
derivadas no mesmo `(contractual_id, asset)`.
"""

import pytest

from pyauditor.excel.report import compute_report_glosa
from pyauditor.rom.summary import IndicatorSummary


def _summary(
    indicator_id: str,
    contractual_id: str,
    *,
    asset: str | None = None,
    penalty_points: float = 0.0,
) -> IndicatorSummary:
    return IndicatorSummary(
        indicator_id=indicator_id,
        contractual_id=contractual_id,
        name=f'Indicador {contractual_id}',
        asset=asset,
        orgao='MinC',
        shape='ratio',
        target_operator='>=',
        target_value=98.0,
        result_pct=50.0,
        conforms=False,
        penalty_points=penalty_points,
        numerator=1,
        denominator=2,
        hard_failure=False,
    )


def test_soma_pontos_e_calcula_valor_da_glosa() -> None:
    result = compute_report_glosa(
        '2026-06',
        [
            _summary('INMS-1.1', 'INMS 1.1', penalty_points=222.14),
            _summary('INMS-1.11', 'INMS 1.11', penalty_points=695.12),
        ],
        valor_base=100_000.0,
    )

    assert result.total_points == pytest.approx(917.26)
    assert result.percentual_ajuste == pytest.approx(0.91726)
    assert result.valor_da_glosa == pytest.approx(917.26)
    assert result.teto_atingido is False


def test_teto_de_30_com_rollover() -> None:
    result = compute_report_glosa(
        '2026-06',
        [_summary('INMS-1.8', 'INMS 1.8', penalty_points=40_000.0)],
        valor_base=100_000.0,
    )

    assert result.percentual_ajuste == pytest.approx(30.0)
    assert result.teto_atingido is True
    assert result.valor_da_glosa == pytest.approx(30_000.0)
    assert result.saldo_rolado_pct == pytest.approx(10.0)


def test_mes_final_nao_rola_saldo() -> None:
    result = compute_report_glosa(
        '2026-06',
        [_summary('INMS-1.8', 'INMS 1.8', penalty_points=40_000.0)],
        valor_base=100_000.0,
        is_final_month=True,
    )

    assert result.percentual_ajuste == pytest.approx(30.0)
    assert result.saldo_rolado_pct == 0.0


def test_sem_valor_base_calcula_percentual_mas_nao_valor() -> None:
    result = compute_report_glosa(
        '2026-06',
        [_summary('INMS-1.1', 'INMS 1.1', penalty_points=222.14)],
        valor_base=None,
    )

    assert result.percentual_ajuste == pytest.approx(0.22214)
    assert result.valor_da_glosa is None


def test_zero_pontos() -> None:
    result = compute_report_glosa(
        '2026-06',
        [_summary('INMS-1.1', 'INMS 1.1')],
        valor_base=100_000.0,
    )

    assert result.total_points == 0.0
    assert result.percentual_ajuste == pytest.approx(0.0)
    assert result.valor_da_glosa == pytest.approx(0.0)
    assert result.teto_atingido is False


def test_consome_saldo_rolado_do_mes_anterior() -> None:
    result = compute_report_glosa(
        '2026-06',
        [_summary('INMS-1.1', 'INMS 1.1', penalty_points=100.0)],
        valor_base=100_000.0,
        historico={'2026-05': {'saldo_rolado_pct': 15.0}},
    )

    assert result.raw_pct == pytest.approx(15.1)
    assert result.percentual_ajuste == pytest.approx(15.1)
    assert result.teto_atingido is False


def test_categoria_derivada_exclui_base_do_mesmo_contractual() -> None:
    base = _summary('INMS-1.1', 'INMS 1.1', penalty_points=100.0)
    derivada = _summary('INMS 1.1.Remoto', 'INMS 1.1', penalty_points=40.0)

    result = compute_report_glosa(
        '2026-06', [base, derivada], valor_base=100_000.0
    )

    assert result.total_points == pytest.approx(40.0)
    assert result.valor_da_glosa == pytest.approx(40.0)


def test_sem_derivada_considera_a_base() -> None:
    base = _summary('INMS-1.1', 'INMS 1.1', penalty_points=100.0)

    result = compute_report_glosa('2026-06', [base], valor_base=100_000.0)

    assert result.total_points == pytest.approx(100.0)
