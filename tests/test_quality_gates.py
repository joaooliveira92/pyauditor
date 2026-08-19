from pyauditor.config.models import InSetCheck, NotNullCheck, QualityGateCheck
from pyauditor.engine.quality_gates import QualityGateRunner


def test_rejects_rows_violating_checks_with_reason() -> None:
    checks: list[QualityGateCheck] = [
        NotNullCheck(type="not_null", column="DataHoraFim"),
        InSetCheck(type="in_set", column="No prazo", values=["S", "N"]),
    ]
    runner = QualityGateRunner(checks, id_column="Nº Solicitacao")

    report = runner.run(
        [
            {"Nº Solicitacao": "1", "DataHoraFim": "", "No prazo": "S"},
            {"Nº Solicitacao": "2", "DataHoraFim": "01/06/2026", "No prazo": "X"},
            {"Nº Solicitacao": "3", "DataHoraFim": "01/06/2026", "No prazo": "S"},
        ]
    )

    assert [row["Nº Solicitacao"] for row in report.accepted] == ["3"]
    assert [r.row_id for r in report.rejected] == ["1", "2"]
    assert "nulo/vazio" in report.rejected[0].reason
    assert "fora do conjunto permitido" in report.rejected[1].reason
