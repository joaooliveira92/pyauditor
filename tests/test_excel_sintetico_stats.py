"""Unidade de `excel/sintetico/_stats.py` — aritmética pura extraída do
`write_sintetico_workbook` (ticket 04 SRP), testável sem workbook."""

from pyauditor.excel.sintetico._stats import (
    NivelAccumulator,
    compute_stats,
    fmt_pt_br,
    format_duracao,
    format_pct_bruto,
)


def test_compute_stats_conta_dentro_fora_do_prazo() -> None:
    rows = [
        {
            'No prazo': 'S',
            'DataHoraSolicitacao': '01/06/2026 08:00',
            'DataHoraFim': '01/06/2026 10:00',
        },
        {
            'No prazo': 'N',
            'DataHoraSolicitacao': '02/06/2026 08:00',
            'DataHoraFim': '02/06/2026 12:00',
        },
    ]
    stats = compute_stats(
        rows,
        fieldnames=['No prazo', 'DataHoraSolicitacao', 'DataHoraFim'],
        accepted_ids=set(),
    )
    assert stats.linhas == 2
    assert stats.dentro == 1
    assert stats.fora == 1


def test_compute_stats_sem_coluna_no_prazo_nao_conta_dentro_fora() -> None:
    rows = [
        {
            'DataHoraSolicitacao': '01/06/2026 08:00',
            'DataHoraFim': '01/06/2026 10:00',
        }
    ]
    stats = compute_stats(
        rows,
        fieldnames=['DataHoraSolicitacao', 'DataHoraFim'],
        accepted_ids=set(),
    )
    assert stats.dentro is None
    assert stats.fora is None


def test_compute_stats_ignora_linhas_nao_aprovadas_no_tempo_medio() -> None:
    rows = [
        {
            'No prazo': 'S',
            'DataHoraSolicitacao': '01/06/2026 08:00',
            'DataHoraFim': '01/06/2026 10:00',
        },
        {
            'No prazo': 'N',
            'DataHoraSolicitacao': '02/06/2026 08:00',
            'DataHoraFim': '02/06/2026 12:00',
        },
    ]
    # Uma única linha aprovada (a segunda) — duração de 4h.
    only_second = [rows[1]]
    stats = compute_stats(
        only_second,
        fieldnames=['No prazo', 'DataHoraSolicitacao', 'DataHoraFim'],
        accepted_ids={id(rows[1])},
    )
    assert stats.duracao_contagem == 1
    assert stats.duracao_total_segundos == 4 * 3600


def test_format_duracao_multi_dia() -> None:
    assert format_duracao(48 * 3600) == '2d 00h'
    assert format_duracao((25 * 60 + 30) * 60) == '1d 01h'


def test_fmt_pt_br_usa_virgula() -> None:
    assert fmt_pt_br(12.5) == '12,5'
    assert fmt_pt_br(3.14159, decimals=3) == '3,142'


def test_format_pct_bruto_quando_sem_prazo() -> None:
    assert format_pct_bruto(None, None) == '—'
    assert format_pct_bruto(0, 0) == '—'


def test_nivel_accumulator_acumula_sem_prazo() -> None:
    from pyauditor.excel.sintetico._stats import Stats

    acc = NivelAccumulator()
    acc = acc.add(
        Stats(
            linhas=1,
            dentro=None,
            fora=None,
            duracao_total_segundos=0.0,
            duracao_contagem=0,
        )
    )
    assert acc.tem_prazo is False
