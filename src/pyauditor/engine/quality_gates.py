"""Data-layer validation: does each CSV row satisfy the YAML's
`quality_gates.checks`?

Distinct from Pydantic's config-layer validation (see docs/spec/inms-pipeline.md
§4) — this runs after the CSV is parsed and produces the rejected-rows report
that feeds the ROM.
"""

from dataclasses import dataclass

from pyauditor.config.models import InSetCheck, NotNullCheck, QualityGateCheck


@dataclass(frozen=True)
class RejectedRow:
    row_id: str
    reason: str


@dataclass(frozen=True)
class QualityGateReport:
    accepted: list[dict[str, str]]
    rejected: list[RejectedRow]


class QualityGateRunner:
    def __init__(self, checks: list[QualityGateCheck], id_column: str) -> None:
        self._checks = checks
        self._id_column = id_column

    def run(self, rows: list[dict[str, str]]) -> QualityGateReport:
        accepted: list[dict[str, str]] = []
        rejected: list[RejectedRow] = []
        for row in rows:
            reason = self._first_violation(row)
            if reason is None:
                accepted.append(row)
            else:
                if self._id_column not in row:
                    raise ValueError(
                        f'id_column {self._id_column!r} não existe no '
                        f'header do CSV '
                        '— corrija source.id_column na config do indicador'
                    )
                rejected.append(
                    RejectedRow(row_id=row[self._id_column], reason=reason)
                )
        return QualityGateReport(accepted=accepted, rejected=rejected)

    def _first_violation(self, row: dict[str, str]) -> str | None:
        for check in self._checks:
            if isinstance(check, NotNullCheck):
                value = row.get(check.column, '').strip()
                if not value or value.lower() == 'null':
                    return f"'{check.column}' é nulo/vazio"
            elif isinstance(check, InSetCheck):
                value = row.get(check.column, '').strip()
                if value not in check.values:
                    return (
                        f"'{check.column}'"
                        f'='
                        f"'{value}' "
                        f'fora '
                        f'do '
                        f'conjunto '
                        f'permitido '
                        f'{check.values}'
                    )
        return None
