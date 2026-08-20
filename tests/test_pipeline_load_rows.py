from pathlib import Path

import pytest

from pyauditor.engine.pipeline import load_rows


def test_load_rows_reads_and_strips_delimited_values(tmp_path: Path) -> None:
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("a;b\n 1 ; 2 \n", encoding="utf-8")

    rows = load_rows(csv_path, delimiter=";", encoding="utf-8")

    assert rows == [{"a": "1", "b": "2"}]


def test_load_rows_rejects_a_headerless_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="sem linha de cabeçalho"):
        load_rows(csv_path, delimiter=";", encoding="utf-8")
