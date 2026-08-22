"""Derive reporting periods and filter dataset rows by competence.

The reporting competence supplied by the CLI is the only source used to
derive the measurement window. This module does not read period information
from cover files and does not infer the reporting competence from dataset
contents.

Two cell formats are recognized:

- ``DD/MM/YYYY HH:MM`` represents one calendar day;
- ``YYYY-MM`` represents the complete calendar month.

Other values, including invalid dates and times, are classified as undated.
In the default mode, undated rows remain available for downstream quality
gates. In strict mode, they are discarded.

The filtering operation performs no logging or I/O. It preserves row order,
returns shallow copies of retained rows, and reports separate counts for rows
outside the period and undated rows discarded by strict mode.
"""

from __future__ import annotations

import calendar
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Final

__all__: Final[tuple[str, ...]] = (
    "PeriodColumnMissingError",
    "PeriodColumnNotFoundError",
    "PeriodFilterResult",
    "PeriodoAfericao",
    "discard_message",
    "empty_window_message",
    "filter_periodo",
    "format_date_br",
    "format_period_br",
    "month_bounds",
    "require_period_column",
)

_DATETIME_CELL_FORMAT: Final[str] = "%d/%m/%Y %H:%M"
_MONTH_CELL_RE: Final[re.Pattern[str]] = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])$")
_COMPETENCIA_RE: Final[re.Pattern[str]] = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])$")


@dataclass(frozen=True, slots=True)
class PeriodoAfericao:
    """Represent an inclusive measurement window.

    Attributes:
        inicio: First date included in the measurement window.
        fim: Last date included in the measurement window.

    Raises:
        TypeError: If either boundary is not a ``date``.
        ValueError: If the final date precedes the initial date.
    """

    inicio: date
    fim: date

    def __post_init__(self) -> None:
        """Validate the inclusive date interval."""
        if not isinstance(self.inicio, date):
            raise TypeError(f"inicio must be a date, received {type(self.inicio).__name__}.")

        if not isinstance(self.fim, date):
            raise TypeError(f"fim must be a date, received {type(self.fim).__name__}.")

        if self.fim < self.inicio:
            raise ValueError(
                "fim must not precede inicio: "
                f"inicio={self.inicio.isoformat()}, "
                f"fim={self.fim.isoformat()}."
            )


@dataclass(frozen=True, slots=True)
class PeriodFilterResult:
    """Contain retained rows and period-filtering counters.

    Retained rows are shallow copies of the input mappings. Mutating a
    returned row therefore does not mutate the corresponding input row.

    Attributes:
        linhas_na_janela: Rows retained in their original order.
        dropped_out_of_period: Number of dated rows outside the window.
        undated_dropped: Number of undated rows discarded by strict mode.
    """

    linhas_na_janela: list[dict[str, str]]
    dropped_out_of_period: int
    undated_dropped: int


class PeriodColumnMissingError(ValueError):
    """Report a configuration without ``source.period_column``."""


class PeriodColumnNotFoundError(ValueError):
    """Report a declared period column absent from a dataset row."""


def month_bounds(competencia: str) -> PeriodoAfericao:
    """Derive the inclusive calendar-month window for a competence.

    Args:
        competencia: Reporting competence in ``YYYY-MM`` format.

    Returns:
        An inclusive interval covering the complete calendar month.

    Raises:
        TypeError: If ``competencia`` is not a string.
        ValueError: If the value does not use ``YYYY-MM`` or contains an
            invalid calendar year or month.
    """
    if not isinstance(competencia, str):
        raise TypeError(f"competencia must be a string, received {type(competencia).__name__}.")

    if _COMPETENCIA_RE.fullmatch(competencia) is None:
        raise ValueError(
            f"competência inválida: {competencia!r}; esperado AAAA-MM com mês entre 01 e 12"
        )

    year = int(competencia[:4])
    month = int(competencia[5:7])

    try:
        first_day = date(year, month, 1)
        last_day = date(
            year,
            month,
            calendar.monthrange(year, month)[1],
        )
    except ValueError as exc:
        raise ValueError(
            f"competência inválida: {competencia!r}; ano e mês devem formar uma data válida"
        ) from exc

    return PeriodoAfericao(
        inicio=first_day,
        fim=last_day,
    )


def require_period_column(
    period_column: str | None,
    *,
    config_path: Path | str | None = None,
) -> str:
    """Return the configured period column or raise an actionable error.

    Args:
        period_column: Value of ``source.period_column`` from configuration.
        config_path: Optional configuration path included in the error.

    Returns:
        The stripped, non-empty period-column name.

    Raises:
        TypeError: If ``period_column`` is neither a string nor ``None``.
        PeriodColumnMissingError: If the configured value is absent or empty.
    """
    if period_column is not None and not isinstance(period_column, str):
        raise TypeError(
            f"period_column must be a string or None, received {type(period_column).__name__}."
        )

    column = (period_column or "").strip()
    if column:
        return column

    origin = f" em {config_path}" if config_path is not None else ""
    raise PeriodColumnMissingError(
        f"source.period_column não declarado{origin}; "
        "indique no YAML a coluna de período do dataset para que o pipeline "
        "possa filtrar a janela da competência"
    )


def _cell_interval(
    cell_value: str | None,
) -> tuple[date, date] | None:
    """Convert a recognized period cell into its covered interval.

    Invalid and unsupported values are classified as undated and return
    ``None``. This includes invalid calendar dates, invalid times, empty
    values, and strings outside the two supported formats.
    """
    if cell_value is not None and not isinstance(cell_value, str):
        return None

    text = (cell_value or "").strip()
    if not text:
        return None

    try:
        timestamp = datetime.strptime(
            text,
            _DATETIME_CELL_FORMAT,
        )
    except ValueError:
        pass
    else:
        day = timestamp.date()
        return day, day

    if _MONTH_CELL_RE.fullmatch(text) is None:
        return None

    year = int(text[:4])
    month = int(text[5:7])

    try:
        first_day = date(year, month, 1)
        last_day = date(
            year,
            month,
            calendar.monthrange(year, month)[1],
        )
    except ValueError:
        return None

    return first_day, last_day


def filter_periodo(
    linhas: Sequence[Mapping[str, str]],
    *,
    period_column: str,
    periodo: PeriodoAfericao,
    strict: bool = False,
) -> PeriodFilterResult:
    """Filter dataset rows against an inclusive measurement window.

    A row is retained when its parsed interval intersects the measurement
    window. A readable date outside the window is always discarded.

    A cell with no recognized date is retained in default mode so downstream
    quality gates can evaluate it. Under strict mode, the row is discarded
    and counted in ``undated_dropped``.

    A row that does not contain the declared period column is treated as an
    undated row: in default mode it is retained for the quality gates, and in
    strict mode it is discarded and counted. Row-level column absence is
    therefore never treated as a dataset-schema error — callers that must
    reject a missing column outright check the header before filtering.

    Input mappings are never modified. Retained rows are shallow-copied into
    ordinary dictionaries, and their original order is preserved.

    Args:
        linhas: Dataset rows to filter.
        period_column: Declared period-column name.
        periodo: Inclusive measurement window.
        strict: Whether rows without a readable period must be discarded.

    Returns:
        Retained rows and separate discard counters.

    Raises:
        TypeError: If arguments violate their runtime type contracts.
        ValueError: If ``period_column`` is empty.
    """
    if not isinstance(period_column, str):
        raise TypeError(f"period_column must be a string, received {type(period_column).__name__}.")

    normalized_column = period_column.strip()
    if not normalized_column:
        raise ValueError("period_column must not be empty.")

    if not isinstance(periodo, PeriodoAfericao):
        raise TypeError(f"periodo must be PeriodoAfericao, received {type(periodo).__name__}.")

    if not isinstance(strict, bool):
        raise TypeError(f"strict must be bool, received {type(strict).__name__}.")

    retained_rows: list[dict[str, str]] = []
    dropped_out_of_period = 0
    undated_dropped = 0

    for row_index, row in enumerate(linhas, start=1):
        if not isinstance(row, Mapping):
            raise TypeError(
                f"linhas[{row_index - 1}] must be a mapping, received {type(row).__name__}."
            )

        cell_value = row.get(normalized_column)
        interval = None if cell_value is None else _cell_interval(cell_value)

        if interval is None:
            if strict:
                undated_dropped += 1
            else:
                retained_rows.append(dict(row))
            continue

        intersects_window = interval[1] >= periodo.inicio and interval[0] <= periodo.fim

        if intersects_window:
            retained_rows.append(dict(row))
        else:
            dropped_out_of_period += 1

    return PeriodFilterResult(
        linhas_na_janela=retained_rows,
        dropped_out_of_period=dropped_out_of_period,
        undated_dropped=undated_dropped,
    )


def format_date_br(data: date) -> str:
    """Format a date as ``DD/MM/YYYY``.

    Args:
        data: Date to format.

    Returns:
        Brazilian calendar-date representation.

    Raises:
        TypeError: If ``data`` is not a date.
    """
    if not isinstance(data, date):
        raise TypeError(f"data must be a date, received {type(data).__name__}.")

    return f"{data.day:02d}/{data.month:02d}/{data.year:04d}"


def format_period_br(periodo: PeriodoAfericao) -> str:
    """Format a measurement window for human-readable output.

    Example:
        ``01/06/2026 a 30/06/2026``
    """
    if not isinstance(periodo, PeriodoAfericao):
        raise TypeError(f"periodo must be PeriodoAfericao, received {type(periodo).__name__}.")

    return f"{format_date_br(periodo.inicio)} a {format_date_br(periodo.fim)}"


def empty_window_message(
    periodo: PeriodoAfericao,
) -> str:
    """Return the diagnostic used when no row remains in the window."""
    if not isinstance(periodo, PeriodoAfericao):
        raise TypeError(f"periodo must be PeriodoAfericao, received {type(periodo).__name__}.")

    return (
        f"nenhuma linha no período {format_date_br(periodo.inicio)}–"
        f"{format_date_br(periodo.fim)} — "
        "o arquivo corresponde à competência?"
    )


def discard_message(
    dropped_out_of_period: int,
    undated_dropped: int,
    strict: bool,
) -> str | None:
    """Build the informational message for discarded dataset rows.

    Undated rows are mentioned only in strict mode because they are retained
    otherwise.

    Args:
        dropped_out_of_period: Number of readable rows outside the window.
        undated_dropped: Number of undated rows discarded by strict mode.
        strict: Whether strict period filtering was enabled.

    Returns:
        A human-readable diagnostic, or ``None`` when no relevant rows were
        discarded.

    Raises:
        TypeError: If counters are not integers or ``strict`` is not boolean.
        ValueError: If either counter is negative.
    """
    _validate_non_negative_count(
        dropped_out_of_period,
        field="dropped_out_of_period",
    )
    _validate_non_negative_count(
        undated_dropped,
        field="undated_dropped",
    )

    if not isinstance(strict, bool):
        raise TypeError(f"strict must be bool, received {type(strict).__name__}.")

    parts: list[str] = []

    if dropped_out_of_period > 0:
        parts.append(f"{dropped_out_of_period} linha(s) fora do período descartada(s)")

    if strict and undated_dropped > 0:
        if parts:
            parts.append(f"{undated_dropped} sem data legível")
        else:
            parts.append(f"{undated_dropped} linha(s) sem data legível descartada(s)")

    if not parts:
        return None

    return " e ".join(parts)


def _validate_non_negative_count(
    value: int,
    *,
    field: str,
) -> None:
    """Validate a non-boolean, non-negative integer counter."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field} must be an integer, received {type(value).__name__}.")

    if value < 0:
        raise ValueError(f"{field} must not be negative, received {value}.")
