"""Testes unitários da aritmética compartilhada de meta/shortfall em `_target`.

Cobre `safe_pct`, `meets_target`, `shortfall` e a regra de denominador zero
centralizada em `ratio_penalty_points` (ticket reducao-friccao/02): uma
estratégia sem atividade elegível (denominador zero) não tem base contra a
qual penalizar — deve marcar 0 pontos, nunca aplicar `shortfall` a um
`safe_pct` que silenciosamente retornou 0.0.
"""

import pytest

from pyauditor.engine.strategies._target import (
    meets_target,
    ratio_penalty_points,
    safe_pct,
    shortfall,
)


def test_safe_pct_returns_percent() -> None:
    assert safe_pct(1, 2) == 50.0


def test_safe_pct_zero_denominator_returns_zero() -> None:
    assert safe_pct(1, 0) == 0.0
    assert safe_pct(0, 0) == 0.0


def test_meets_target_gte() -> None:
    assert meets_target(90.0, '>=', 90.0) is True
    assert meets_target(91.0, '>=', 90.0) is True
    assert meets_target(89.0, '>=', 90.0) is False


def test_meets_target_gte_is_epsilon_forgiving() -> None:
    assert meets_target(90.0 - 1e-12, '>=', 90.0) is True


def test_meets_target_lte() -> None:
    assert meets_target(90.0, '<=', 90.0) is True
    assert meets_target(89.0, '<=', 90.0) is True
    assert meets_target(91.0, '<=', 90.0) is False


def test_shortfall_gte_is_positive_when_below_target() -> None:
    assert shortfall(80.0, '>=', 90.0) == 10.0


def test_shortfall_gte_is_negative_when_above_target() -> None:
    assert shortfall(95.0, '>=', 90.0) == -5.0


def test_shortfall_lte_flips_the_direction() -> None:
    assert shortfall(100.0, '<=', 90.0) == 10.0
    assert shortfall(80.0, '<=', 90.0) == -10.0


def test_ratio_penalty_underperforming_adds_base_and_steps() -> None:
    penalty = ratio_penalty_points(
        numerator=1,
        denominator=2,
        operator='>=',
        target=90.0,
        step_size_pct=0.1,
        step_points=20,
        base_points=5.0,
    )
    # 1/2 = 50%; shortfall = 40; 40/0.1 = 400 degraus * 20 = 8000 + 5.
    assert penalty == 8005.0


def test_ratio_penalty_conforming_is_zero_without_applying_base() -> None:
    penalty = ratio_penalty_points(
        numerator=2,
        denominator=2,
        operator='>=',
        target=90.0,
        step_size_pct=0.1,
        step_points=20,
        base_points=5.0,
    )
    assert penalty == 0.0


def test_ratio_penalty_zero_denominator_never_penalizes() -> None:
    penalty = ratio_penalty_points(
        numerator=0,
        denominator=0,
        operator='>=',
        target=90.0,
        step_size_pct=0.1,
        step_points=20,
        base_points=5.0,
    )
    assert penalty == 0.0


def test_ratio_penalty_is_exact_not_epsilon_forgiving() -> None:
    # Um resultado real abaixo da meta (não só o caminho sem atividade) mantém
    # a penalidade exata de hoje — a função não perdoa um resultado sub-meta
    # dentro do EPSILON como `meets_target` faria (homologação do
    # `segmented_ratio`: números idênticos aos de antes).
    penalty = ratio_penalty_points(
        numerator=899.99999,
        denominator=1000,
        operator='>=',
        target=90.0,
        step_size_pct=0.1,
        step_points=20,
    )
    # 89.999999%; shortfall = 1e-6; 1e-6/0.1 * 20 = 2e-4 — exato, não zerado.
    assert penalty == pytest.approx(2e-4)
