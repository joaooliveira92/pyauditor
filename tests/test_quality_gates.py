from pyauditor.config.models import InSetCheck, NotNullCheck, QualityGateCheck
from pyauditor.engine.quality_gates import QualityGateRunner


def test_rejects_rows_violating_checks_with_reason() -> None:
    checks: list[QualityGateCheck] = [
        NotNullCheck(type='not_null', column='DataHoraFim'),
        InSetCheck(type='in_set', column='No prazo', values=['S', 'N']),
    ]
    runner = QualityGateRunner(checks, id_column='Nº Solicitacao')

    report = runner.run(
        [
            {'Nº Solicitacao': '1', 'DataHoraFim': '', 'No prazo': 'S'},
            {
                'Nº Solicitacao': '2',
                'DataHoraFim': '01/06/2026',
                'No prazo': 'X',
            },
            {
                'Nº Solicitacao': '3',
                'DataHoraFim': '01/06/2026',
                'No prazo': 'S',
            },
        ]
    )

    assert [row['Nº Solicitacao'] for row in report.accepted] == ['3']
    assert [r.row_id for r in report.rejected] == ['1', '2']
    assert 'nulo/vazio' in report.rejected[0].reason
    assert 'fora do conjunto permitido' in report.rejected[1].reason


def test_missing_id_column_on_rejected_row_raises_contextual_error() -> None:
    """Caminho de erro: uma linha rejeitada mas sem a coluna `id_column` no
    header → ValueError acionável em vez de KeyError cru."""
    import pytest

    from pyauditor.engine.quality_gates import QualityGateRunner

    runner = QualityGateRunner(
        [NotNullCheck(type='not_null', column='DataHoraFim')],
        id_column='Nº Solicitacao',
    )

    with pytest.raises(
        ValueError, match="id_column 'Nº Solicitacao' não existe"
    ):
        runner.run([{'DataHoraFim': ''}])
