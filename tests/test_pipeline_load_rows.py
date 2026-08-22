from pathlib import Path

import pytest

from pyauditor.engine.pipeline import load_rows


def test_load_rows_reads_and_strips_delimited_values(tmp_path: Path) -> None:
    csv_path = tmp_path / 'data.csv'
    csv_path.write_text('a;b\n 1 ; 2 \n', encoding='utf-8')

    rows = load_rows(csv_path, delimiter=';', encoding='utf-8')

    assert rows == [{'a': '1', 'b': '2'}]


def test_load_rows_rejects_a_headerless_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / 'empty.csv'
    csv_path.write_text('', encoding='utf-8')

    with pytest.raises(ValueError, match='sem linha de cabeçalho'):
        load_rows(csv_path, delimiter=';', encoding='utf-8')


def test_load_rows_handles_ragged_rows_by_dropping_overflow(
    tmp_path: Path,
) -> None:
    """Linhas ragged (campo livre com o delimiter deslocando colunas) — a
    sobrecarga que o DictReader enfia na chave `None` é descartada; só as
    colunas declaradas sobrevivem."""
    from pyauditor.engine.pipeline import load_rows

    csv_path = tmp_path / 'ragged.csv'
    csv_path.write_text('a;b;c\n1;2;3\n4;5;6;7;8\n', encoding='utf-8')

    rows = load_rows(csv_path, delimiter=';', encoding='utf-8')

    assert rows == [
        {'a': '1', 'b': '2', 'c': '3'},
        {'a': '4', 'b': '5', 'c': '6'},
    ]


def test_read_raw_csv_normalizes_grupo_executor_header_alias(
    tmp_path: Path,
) -> None:
    """Header com alias `Grupo executor` (espaço) é normalizado para
    `Grupo_executor` na leitura — mesmo contrato do backbone."""
    from pyauditor.categoria_filter import GRUPO_EXECUTOR_COLUMN, read_raw_csv

    csv_path = tmp_path / 'alias.csv'
    csv_path.write_text('N;Grupo executor;v\n1;N1;x\n', encoding='utf-8')

    fieldnames, rows = read_raw_csv(csv_path, delimiter=';', encoding='utf-8')

    assert GRUPO_EXECUTOR_COLUMN in fieldnames
    assert rows == [{GRUPO_EXECUTOR_COLUMN: 'N1', 'N': '1', 'v': 'x'}]


def test_detect_delimiter_switches_when_configured_absent_from_header(
    tmp_path: Path,
) -> None:
    """Export diverge do delimiter configurado (fato de produção 2026-06):
    `_detect_delimiter` troca para o candidato presente no cabeçalho."""
    from pyauditor.engine.loading import _detect_delimiter

    csv_path = tmp_path / 'comma.csv'
    csv_path.write_text('a,b\n1,2\n', encoding='utf-8')

    detected = _detect_delimiter(csv_path, 'utf-8', configured=';')

    assert detected == ','


def test_detect_delimiter_respects_uncommon_explicit_delimiter(
    tmp_path: Path,
) -> None:
    """Delimiter incomum e explícito não é adivinhado — é respeitado."""
    from pyauditor.engine.loading import _detect_delimiter

    csv_path = tmp_path / 'tab.tsv'
    csv_path.write_text('a\tb\n', encoding='utf-8')

    assert _detect_delimiter(csv_path, 'utf-8', configured='\t') == '\t'
