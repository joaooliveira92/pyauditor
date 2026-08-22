"""Unidade de `excel/consolidate/_glosa_calcs.py` — a aritmética da glosa
consolidada testada fora do workbook (ticket 04 SRP)."""

from pyauditor.excel.consolidate._glosa_calcs import (
    accumulate_pontos_por_orgao,
    compute_aggregation,
    is_amnestied,
)
from pyauditor.rom.summary import IndicatorSummary


def _summary(
    contractual_id: str, orgao: str = 'MinC', *, penalty_points: float = 100.0
) -> IndicatorSummary:
    return IndicatorSummary(
        indicator_id=f'{contractual_id}-IND',
        contractual_id=contractual_id,
        name=f'Indicador {contractual_id}',
        asset=None,
        orgao=orgao,
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


def test_accumulate_pontos_por_orgao_respects_amnesty() -> None:
    decisions: dict[tuple[str, str], dict[str, object]] = {
        ('INMS 1.01', 'MinC'): {'Decisão Fiscal': 'Aceita'},
        ('INMS 1.02', 'MinC'): {'Decisão Fiscal': 'não aceita'},
    }
    minc = [
        _summary('INMS 1.1', orgao='MinC', penalty_points=100.0),
        _summary('INMS 1.2', orgao='MinC', penalty_points=50.0),
    ]
    pontos, seen = accumulate_pontos_por_orgao(minc, [], decisions)
    assert pontos == {'MinC': 50.0, 'MTur': 0.0}
    assert len(seen) == 2
    assert ('INMS 1.01', 'MinC') in seen


def test_is_amnestied_folds_matching_prefix() -> None:
    assert is_amnestied({'Decisão Fiscal': 'Aceita'}) is True
    assert is_amnestied({'Decisão Fiscal': 'aceita a justificativa'}) is True
    assert is_amnestied({'Decisão Fiscal': 'rejeitada'}) is False
    assert is_amnestied({}) is False


def test_compute_aggregation_rateia_saldo_e_soma_glosas() -> None:
    pontos = {'MinC': 100.0, 'MTur': 200.0}
    resultado = compute_aggregation(
        pontos_por_orgao=pontos,
        valor_base=10000.0,
        competencia='2026-06',
        historico=None,
        is_final_month=False,
    )
    # Glosa por-órgão = pontos * FOICTA_PERCENT * valor_base; cada um com o
    # mesmo valor_base (simplificação: soma direta dos valores por-órgão).
    assert resultado.total_pontos > 0
    assert resultado.glosa_final > 0
    assert resultado.pct_bruto > 0
    assert resultado.aplicado <= 100.0
