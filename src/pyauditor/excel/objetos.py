"""Read contractual monthly values from ``input/objetos.csv``.

The file is the canonical monetary source for contractual items and must use
the following exact schema:

    Item,Categoria,Valor

Each row represents one contractual item:

- ``Item`` is a positive, contiguous, one-based integer;
- ``Categoria`` is a non-empty descriptive value;
- ``Valor`` is the contractual monthly value.

Monetary values may use Brazilian currency notation, such as
``R$ 148.205,54``, or plain machine notation, such as ``148205.54``.
Brazilian thousands separators are optional, but decimal values must contain
exactly two fractional digits.

Values are represented with :class:`decimal.Decimal` to avoid binary
floating-point errors in contractual totals. The monthly total is the exact
sum of all item values. The annual total is the monthly total multiplied by
twelve.

The file contains no separate summary row. Therefore, there is no
fiscal-declared total to reconcile against the calculated totals.

A missing file is not handled here. ``FileNotFoundError`` propagates so the
caller can decide whether the absence represents incomplete input or a fatal
condition.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Final

__all__: Final[tuple[str, ...]] = (
    "OBJETOS_DELIMITER",
    "OBJETOS_ENCODING",
    "OBJETOS_FILENAME",
    "Objetos",
    "parse_brl_value",
    "read_objetos",
)

OBJETOS_FILENAME: Final[str] = "objetos.csv"
OBJETOS_DELIMITER: Final[str] = ","
OBJETOS_ENCODING: Final[str] = "utf-8-sig"

_ITEM_HEADER: Final[str] = "Item"
_CATEGORIA_HEADER: Final[str] = "Categoria"
_VALOR_HEADER: Final[str] = "Valor"

_EXPECTED_HEADERS: Final[tuple[str, ...]] = (
    _ITEM_HEADER,
    _CATEGORIA_HEADER,
    _VALOR_HEADER,
)

_MONTHS_PER_YEAR: Final[Decimal] = Decimal("12")
_ZERO: Final[Decimal] = Decimal("0.00")

_PT_BR_MONEY_RE: Final[re.Pattern[str]] = re.compile(
    r"""
    ^\s*
    (?:R\$\s*)?
    (?P<integer>
        0
        |
        [1-9]\d*
        |
        [1-9]\d{0,2}(?:\.\d{3})+
    )
    (?P<decimal>,\d{2})?
    \s*$
    """,
    re.VERBOSE,
)

_MACHINE_MONEY_RE: Final[re.Pattern[str]] = re.compile(
    r"""
    ^\s*
    (?P<integer>0|[1-9]\d*)
    (?P<decimal>\.\d{2})?
    \s*$
    """,
    re.VERBOSE,
)


@dataclass(frozen=True, slots=True)
class Objetos:
    """Represent validated contractual item values and derived totals.

    Attributes:
        itens: Monthly values ordered by their one-based contractual item
            index. Position zero corresponds to contractual item 1.
        total_mensal: Exact sum of all monthly item values.
        total_anual: Monthly total multiplied by twelve.
        warnings: Non-fatal diagnostics produced while reading the file.
            The current strict parser does not emit warnings, but the field is
            retained as part of the established result contract.
    """

    itens: tuple[Decimal, ...]
    total_mensal: Decimal
    total_anual: Decimal
    warnings: tuple[str, ...]


def parse_brl_value(text: str) -> Decimal:
    """Parse a supported monetary value into an exact decimal.

    Accepted Brazilian representations include:

    - ``R$ 148.205,54``;
    - ``148.205,54``;
    - ``148205,54``;
    - ``148205``;
    - ``R$ 0,00``.

    Accepted machine representations include:

    - ``148205.54``;
    - ``148205``;
    - ``0.00``.

    Thousands separators must follow Brazilian grouping rules. Decimal
    values must contain exactly two fractional digits. Negative values,
    malformed separators, currency symbols other than ``R$``, and non-numeric
    values are rejected.

    Args:
        text: Raw monetary field read from the CSV file.

    Returns:
        The parsed non-negative monetary value as ``Decimal``.

    Raises:
        TypeError: If ``text`` is not a string.
        ValueError: If the value does not match a supported monetary format.
    """
    if not isinstance(text, str):
        raise TypeError(
            f"Monetary value must be a string, received {type(text).__name__}."
        )

    pt_br_match = _PT_BR_MONEY_RE.fullmatch(text)
    if pt_br_match is not None:
        integer_part = pt_br_match.group("integer").replace(".", "")
        decimal_part = pt_br_match.group("decimal") or ",00"
        normalized = f"{integer_part}.{decimal_part[1:]}"
        return _to_decimal(normalized, original=text)

    machine_match = _MACHINE_MONEY_RE.fullmatch(text)
    if machine_match is not None:
        integer_part = machine_match.group("integer")
        decimal_part = machine_match.group("decimal") or ".00"
        normalized = f"{integer_part}{decimal_part}"
        return _to_decimal(normalized, original=text)

    raise ValueError(f"Invalid monetary value: {text!r}.")


def read_objetos(path: Path) -> Objetos:
    """Read and validate the contractual monetary source.

    The header must match ``Item,Categoria,Valor`` exactly, including column
    order and spelling. Every data row must contain exactly three fields.

    Item indexes may appear in any row order, but after sorting they must form
    the contiguous sequence ``1..N``. Duplicate indexes, missing indexes, zero,
    and negative indexes are rejected.

    At least one contractual item is required. Categories must be non-empty,
    and monetary fields must satisfy :func:`parse_brl_value`.

    Args:
        path: Path to ``objetos.csv``.

    Returns:
        Validated item values ordered by item index, together with exact
        monthly and annual totals.

    Raises:
        FileNotFoundError: If the input file does not exist.
        IsADirectoryError: If ``path`` refers to a directory.
        PermissionError: If filesystem permissions prevent reading the file.
        UnicodeDecodeError: If the file cannot be decoded as UTF-8.
        csv.Error: If the CSV parser encounters malformed CSV syntax.
        ValueError: If the header, row structure, item indexes, categories, or
            monetary values violate the file contract.
    """
    indexed_values: list[tuple[int, Decimal]] = []

    with path.open(
        mode="r",
        encoding=OBJETOS_ENCODING,
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle,
            delimiter=OBJETOS_DELIMITER,
            strict=True,
        )

        if reader.fieldnames is None:
            raise ValueError(f"{path}: CSV is empty or has no header.")

        actual_headers = tuple(reader.fieldnames)
        if actual_headers != _EXPECTED_HEADERS:
            expected = OBJETOS_DELIMITER.join(_EXPECTED_HEADERS)
            actual = OBJETOS_DELIMITER.join(actual_headers)
            raise ValueError(
                f"{path}: invalid header: expected {expected!r}, "
                f"received {actual!r}."
            )

        for row in reader:
            line_number = reader.line_num
            _validate_row_structure(
                path=path,
                line_number=line_number,
                row=row,
            )

            item_raw = _required_field(
                path=path,
                line_number=line_number,
                row=row,
                header=_ITEM_HEADER,
            )
            categoria = _required_field(
                path=path,
                line_number=line_number,
                row=row,
                header=_CATEGORIA_HEADER,
            )
            valor_raw = _required_field(
                path=path,
                line_number=line_number,
                row=row,
                header=_VALOR_HEADER,
            )

            item = _parse_item_index(
                path=path,
                line_number=line_number,
                value=item_raw,
            )

            if not categoria:
                raise ValueError(
                    f"{path}: line {line_number}: Categoria must not be empty."
                )

            try:
                valor = parse_brl_value(valor_raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"{path}: line {line_number}: invalid Valor for "
                    f"item {item}: {valor_raw!r}."
                ) from exc

            indexed_values.append((item, valor))

    if not indexed_values:
        raise ValueError(f"{path}: CSV contains no contractual items.")

    indexed_values.sort(key=lambda entry: entry[0])
    actual_indexes = tuple(item for item, _ in indexed_values)
    expected_indexes = tuple(range(1, len(indexed_values) + 1))

    if actual_indexes != expected_indexes:
        raise ValueError(
            f"{path}: item indexes must be unique and contiguous from 1: "
            f"expected {expected_indexes!r}, received {actual_indexes!r}."
        )

    item_values = tuple(value for _, value in indexed_values)
    total_mensal = sum(item_values, start=_ZERO)
    total_anual = total_mensal * _MONTHS_PER_YEAR

    return Objetos(
        itens=item_values,
        total_mensal=total_mensal,
        total_anual=total_anual,
        warnings=(),
    )


def _to_decimal(normalized: str, *, original: str) -> Decimal:
    """Convert a normalized monetary string into ``Decimal``."""
    try:
        value = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid monetary value: {original!r}.") from exc

    if not value.is_finite():
        raise ValueError(f"Monetary value must be finite: {original!r}.")

    if value < _ZERO:
        raise ValueError(
            f"Monetary value must not be negative: {original!r}."
        )

    return value


def _validate_row_structure(
    *,
    path: Path,
    line_number: int,
    row: dict[str | None, str | list[str] | None],
) -> None:
    """Validate that a CSV row contains exactly the expected fields."""
    extra_fields = row.get(None)
    if extra_fields:
        raise ValueError(
            f"{path}: line {line_number}: unexpected extra fields: "
            f"{extra_fields!r}."
        )

    missing_headers = tuple(
        header
        for header in _EXPECTED_HEADERS
        if row.get(header) is None
    )
    if missing_headers:
        raise ValueError(
            f"{path}: line {line_number}: missing fields for columns "
            f"{missing_headers!r}."
        )


def _required_field(
    *,
    path: Path,
    line_number: int,
    row: dict[str | None, str | list[str] | None],
    header: str,
) -> str:
    """Return a stripped scalar field from a structurally valid CSV row."""
    value = row.get(header)

    if not isinstance(value, str):
        raise ValueError(
            f"{path}: line {line_number}: field {header!r} must be scalar."
        )

    stripped = value.strip()
    if not stripped:
        raise ValueError(
            f"{path}: line {line_number}: field {header!r} must not be empty."
        )

    return stripped


def _parse_item_index(
    *,
    path: Path,
    line_number: int,
    value: str,
) -> int:
    """Parse and validate a positive contractual item index."""
    if not value.isascii() or not value.isdecimal():
        raise ValueError(
            f"{path}: line {line_number}: Item must be a positive ASCII "
            f"integer, received {value!r}."
        )

    item = int(value)
    if item < 1:
        raise ValueError(
            f"{path}: line {line_number}: Item must be at least 1, "
            f"received {item}."
        )

    return item