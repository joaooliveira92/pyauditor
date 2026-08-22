"""Build synthetic MinC/MTur rows for the consolidated INMS_BASE view.

The consolidated result follows ``docs/spreadsheet.md``:

    (MinC numerator + MTur numerator)
    / (MinC denominator + MTur denominator)

A synthetic ``Consolidado`` row is created only when compatible MinC and MTur
summaries exist for the same contractual indicator, measured indicator, and
asset.

Per-asset availability indicators listed in
``PER_ASSET_CONTRACTUAL_IDS`` remain unconsolidated because their contractual
aggregation formula has not been established from a primary source.

This module affects only the consolidated ``INMS_BASE`` view. Synthetic rows
carry no penalty points and must not be used in financial calculations.

Original summaries are preserved unchanged at the beginning of the returned
list. Synthetic consolidated rows are appended in the order in which their
pairing keys first appear in the input.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from math import isfinite
from typing import Final

from pyauditor.excel.groups import PER_ASSET_CONTRACTUAL_IDS
from pyauditor.rom.summary import IndicatorSummary

__all__: Final[tuple[str, ...]] = ('with_orgao_consolidation',)

_CONSOLIDATABLE_SHAPES: Final[frozenset[str]] = frozenset(
    {
        'ratio',
        'segmented_ratio',
        'count_difference',
    }
)
_EPSILON: Final[float] = 1e-9

_MINC_ORGAO: Final[str] = 'MinC'
_MTUR_ORGAO: Final[str] = 'MTur'
_CONSOLIDATED_ORGAO: Final[str] = 'Consolidado'

_SUPPORTED_ORGAOS: Final[frozenset[str]] = frozenset(
    {
        _MINC_ORGAO,
        _MTUR_ORGAO,
    }
)

type SummaryKey = tuple[str, str, str | None]


def with_orgao_consolidation(
    summaries: Sequence[IndicatorSummary],
) -> list[IndicatorSummary]:
    """Append compatible MinC/MTur consolidated rows.

    Summaries are paired by contractual identifier, measured indicator
    identifier, and asset. Including the measured indicator identifier keeps
    split categories distinct when they share the same contractual identifier
    and asset.

    A synthetic row is created when:

    - both MinC and MTur summaries exist for the same pairing key;
    - the contractual indicator is not excluded as per-asset;
    - both summaries use the same supported calculation shape;
    - both summaries have compatible target metadata;
    - both summaries contain numerators and denominators;
    - both denominators are finite and non-negative;
    - the pooled denominator is strictly positive.

    Summaries from organizations other than MinC and MTur are preserved but do
    not participate in consolidation.

    Args:
        summaries: Measured summaries to preserve and, where possible,
            consolidate. The input sequence is not modified.

    Returns:
        A new list containing all original summaries followed by the synthetic
        consolidated rows.

    Raises:
        ValueError: If duplicate summaries exist for the same pairing key and
            organization, or if a MinC/MTur pair has incompatible structural
            metadata or invalid numeric operands.
    """
    summaries_by_key: dict[
        SummaryKey,
        dict[str, IndicatorSummary],
    ] = {}

    for summary in summaries:
        if summary.orgao not in _SUPPORTED_ORGAOS:
            continue

        key = _summary_key(summary)
        summaries_by_orgao = summaries_by_key.setdefault(key, {})

        if summary.orgao in summaries_by_orgao:
            raise ValueError(
                'Duplicate indicator summary for consolidation: '
                f'contractual_id={summary.contractual_id!r}, '
                f'indicator_id={summary.indicator_id!r}, '
                f'asset={summary.asset!r}, '
                f'orgao={summary.orgao!r}.'
            )

        summaries_by_orgao[summary.orgao] = summary

    rows = list(summaries)

    for summaries_by_orgao in summaries_by_key.values():
        minc = summaries_by_orgao.get(_MINC_ORGAO)
        mtur = summaries_by_orgao.get(_MTUR_ORGAO)

        if minc is None or mtur is None:
            continue

        if minc.contractual_id in PER_ASSET_CONTRACTUAL_IDS:
            continue

        consolidated = _consolidate(minc, mtur)
        if consolidated is not None:
            rows.append(consolidated)

    return rows


def _summary_key(summary: IndicatorSummary) -> SummaryKey:
    """Return the identity used to pair summaries across organizations."""
    return (
        summary.contractual_id,
        summary.indicator_id,
        summary.asset,
    )


def _consolidate(
    minc: IndicatorSummary,
    mtur: IndicatorSummary,
) -> IndicatorSummary | None:
    """Create a synthetic summary from a compatible MinC/MTur pair.

    Unsupported calculation shapes and summaries with missing measurement
    operands are not consolidated.

    Structural incompatibilities and invalid numeric operands raise an error
    because silently selecting metadata from one organization could produce a
    misleading consolidated result.

    The synthetic row receives zero penalty points because it exists only for
    the consolidated analytical view. Financial calculations must continue to
    use the original per-organization summaries.

    Args:
        minc: MinC summary.
        mtur: MTur summary for the same measured indicator and asset.

    Returns:
        The synthetic consolidated summary, or ``None`` when the calculation
        shape is unsupported, measurement operands are absent, or the pooled
        denominator is zero (e.g. both organizations had zero activity for
        the indicator that month — a valid state, not invalid data).

    Raises:
        ValueError: If the pair has mismatched identity, shape or target
            metadata, or contains invalid numeric operands.
    """
    _validate_pair_identity(minc, mtur)
    _validate_pair_contract(minc, mtur)

    if minc.shape not in _CONSOLIDATABLE_SHAPES:
        return None

    if (
        minc.numerator is None
        or minc.denominator is None
        or mtur.numerator is None
        or mtur.denominator is None
    ):
        return None

    minc_numerator = _require_finite_number(
        minc.numerator,
        field='numerator',
        orgao=minc.orgao,
    )
    minc_denominator = _require_nonnegative_number(
        minc.denominator,
        field='denominator',
        orgao=minc.orgao,
    )
    mtur_numerator = _require_finite_number(
        mtur.numerator,
        field='numerator',
        orgao=mtur.orgao,
    )
    mtur_denominator = _require_nonnegative_number(
        mtur.denominator,
        field='denominator',
        orgao=mtur.orgao,
    )

    pooled_numerator = minc_numerator + mtur_numerator
    pooled_denominator = minc_denominator + mtur_denominator
    if pooled_denominator <= 0:
        return None
    result_pct = pooled_numerator / pooled_denominator * 100.0

    conforms = _meets_target(
        result_pct,
        minc.target_operator,
        minc.target_value,
    )

    return replace(
        minc,
        indicator_id=f'{minc.indicator_id}-CONSOLIDADO',
        orgao=_CONSOLIDATED_ORGAO,
        numerator=pooled_numerator,
        denominator=pooled_denominator,
        result_pct=result_pct,
        conforms=conforms,
        penalty_points=0.0,
    )


def _validate_pair_identity(
    minc: IndicatorSummary,
    mtur: IndicatorSummary,
) -> None:
    """Validate that two summaries represent the same measured item.

    Args:
        minc: Expected MinC summary.
        mtur: Expected MTur summary.

    Raises:
        ValueError: If the summaries have different pairing keys or are not
            associated with the expected organizations.
    """
    minc_key = _summary_key(minc)
    mtur_key = _summary_key(mtur)

    if minc_key != mtur_key:
        raise ValueError(
            'Cannot consolidate summaries with different identities: '
            f'MinC={minc_key!r}, MTur={mtur_key!r}.'
        )

    if minc.orgao != _MINC_ORGAO:
        raise ValueError(
            'Expected a MinC summary as the first consolidation operand, '
            f'received orgao={minc.orgao!r}.'
        )

    if mtur.orgao != _MTUR_ORGAO:
        raise ValueError(
            'Expected an MTur summary as the second consolidation operand, '
            f'received orgao={mtur.orgao!r}.'
        )


def _validate_pair_contract(
    minc: IndicatorSummary,
    mtur: IndicatorSummary,
) -> None:
    """Validate calculation and target compatibility between summaries.

    Raises:
        ValueError: If the summaries have different calculation shapes,
            target operators, or target values.
    """
    if minc.shape != mtur.shape:
        raise ValueError(
            'Cannot consolidate summaries with different calculation shapes: '
            f'indicator_id={minc.indicator_id!r}, '
            f'MinC={minc.shape!r}, '
            f'MTur={mtur.shape!r}.'
        )

    if minc.target_operator != mtur.target_operator:
        raise ValueError(
            'Cannot consolidate summaries with different target operators: '
            f'indicator_id={minc.indicator_id!r}, '
            f'MinC={minc.target_operator!r}, '
            f'MTur={mtur.target_operator!r}.'
        )

    if not _optional_float_equal(
        minc.target_value,
        mtur.target_value,
    ):
        raise ValueError(
            'Cannot consolidate summaries with different target values: '
            f'indicator_id={minc.indicator_id!r}, '
            f'MinC={minc.target_value!r}, '
            f'MTur={mtur.target_value!r}.'
        )


def _optional_float_equal(
    left: float | None,
    right: float | None,
) -> bool:
    """Compare optional floating-point values using the engine tolerance."""
    if left is None or right is None:
        return left is right

    if not isfinite(left) or not isfinite(right):
        return False

    return abs(left - right) <= _EPSILON


def _require_finite_number(
    value: float,
    *,
    field: str,
    orgao: str,
) -> float:
    """Convert a numeric operand to a finite float.

    Args:
        value: Numeric measurement operand.
        field: Field name used in validation errors.
        orgao: Organization associated with the operand.

    Returns:
        The operand converted to ``float``.

    Raises:
        ValueError: If the operand is boolean or not finite.
    """
    if isinstance(value, bool):
        raise ValueError(f'{field} must be numeric for {orgao!r}, not boolean.')

    numeric_value = float(value)

    if not isfinite(numeric_value):
        raise ValueError(f'{field} must be finite for {orgao!r}: {value!r}.')

    return numeric_value


def _require_nonnegative_number(
    value: float,
    *,
    field: str,
    orgao: str,
) -> float:
    """Convert a numeric operand to a non-negative finite float.

    A denominator of zero for a single organization is a valid state — it
    means that organization had no measurable activity for the indicator
    that month, not that the data is invalid.

    Args:
        value: Numeric measurement operand.
        field: Field name used in validation errors.
        orgao: Organization associated with the operand.

    Returns:
        The non-negative operand converted to ``float``.

    Raises:
        ValueError: If the operand is boolean, non-finite, or negative.
    """
    numeric_value = _require_finite_number(
        value,
        field=field,
        orgao=orgao,
    )

    if numeric_value < 0:
        raise ValueError(
            f'{field} must be non-negative for {orgao!r}: {value!r}.'
        )

    return numeric_value


def _meets_target(
    result_pct: float,
    operator: str | None,
    target: float | None,
) -> bool:
    """Evaluate a consolidated result against its target.

    The comparison uses the same floating-point tolerance as the measurement
    engine. A completely absent target means that conformity cannot be
    established and therefore returns ``False``.

    Args:
        result_pct: Consolidated percentage result.
        operator: Supported target operator, ``>=`` or ``<=``.
        target: Target boundary.

    Returns:
        ``True`` when the consolidated result satisfies the target.

    Raises:
        ValueError: If the target definition is incomplete, non-finite, or
            uses an unsupported operator.
    """
    if not isfinite(result_pct):
        raise ValueError(f'Consolidated result must be finite: {result_pct!r}.')

    if operator is None and target is None:
        return False

    if operator is None or target is None:
        raise ValueError(
            'Target operator and target value must either both be set or both '
            'be absent.'
        )

    if not isfinite(target):
        raise ValueError(f'Target value must be finite: {target!r}.')

    if operator == '>=':
        return result_pct >= target - _EPSILON

    if operator == '<=':
        return result_pct <= target + _EPSILON

    raise ValueError(
        f'Unsupported target operator for consolidation: {operator!r}.'
    )
