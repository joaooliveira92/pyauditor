"""Abas verbatim (Capa de CSV, Equipe, Prazos) + anexo de objetos — extraídas
de `excel/sintetico/workbook.py` (ticket 04 SRP).
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from pyauditor.excel._csv_verbatim import read_csv_verbatim
from pyauditor.excel._style import new_sheet, write_row
from pyauditor.excel.capa import CAPA_DELIMITER, CAPA_ENCODING
from pyauditor.excel.objetos import OBJETOS_DELIMITER, OBJETOS_ENCODING
from pyauditor.excel.sintetico._sheets._shared import _CAPA_SHEET_NAME


def _write_csv_verbatim_sheet(
    workbook: Workbook,
    sheet_name: str,
    path: Path,
    *,
    delimiter: str,
    encoding: str,
    warnings: list[str],
) -> tuple[Worksheet, int] | None:
    """Aba de reprodução verbatim de um CSV bruto de `input/`
    (`capa.csv`/`equipe.csv`/`prazos.csv`) — cabeçalho e linhas exatamente
    como estão no arquivo, sem processamento. Devolve `(sheet, última linha
    escrita)` em caso de sucesso (usado por `_write_capa_sheet` pra saber
    onde continuar), ou `None` se a aba não foi gerada."""
    try:
        header, rows = read_csv_verbatim(
            path, delimiter=delimiter, encoding=encoding
        )
    except FileNotFoundError:
        warnings.append(
            f"sintetico.xlsx: {path} não encontrado — aba '{sheet_name}' não"
            f'gerada'
        )
        return None
    except (OSError, ValueError) as exc:
        warnings.append(
            f"sintetico.xlsx: falha ao ler {path}: {exc} — aba '{sheet_name}'"
            f'não gerada'
        )
        return None

    sheet = new_sheet(workbook, sheet_name, tuple(header))

    expected_columns = sheet.max_column
    row_idx = 1
    for row_idx, row in enumerate(rows, start=2):
        padded_row = tuple(row) + (None,) * (expected_columns - len(row))
        write_row(sheet, row_idx, padded_row[:expected_columns])
    return sheet, row_idx


def _write_capa_sheet(
    workbook: Workbook,
    capa_path: Path,
    objetos_path: Path | None,
    warnings: list[str],
) -> None:
    """Aba "Capa": reprodução verbatim de `capa.csv`. Quando `objetos_path`
    é passado, `objetos.csv` é anexado logo abaixo (a pedido do usuário: não
    vira aba própria, fica junto da capa, depois da última linha — "Término
    da vigência" no CSV atual), separado por uma linha em branco e o próprio
    cabeçalho de `objetos.csv`."""
    written = _write_csv_verbatim_sheet(
        workbook,
        _CAPA_SHEET_NAME,
        capa_path,
        delimiter=CAPA_DELIMITER,
        encoding=CAPA_ENCODING,
        warnings=warnings,
    )
    if written is None or objetos_path is None:
        return
    sheet, last_row = written

    try:
        objetos_header, objetos_rows = read_csv_verbatim(
            objetos_path, delimiter=OBJETOS_DELIMITER, encoding=OBJETOS_ENCODING
        )
    except FileNotFoundError:
        warnings.append(
            f'sintetico.xlsx: {objetos_path} não encontrado — dados de objetos '
            f"não anexados à aba '{_CAPA_SHEET_NAME}'"
        )
        return
    except (OSError, ValueError) as exc:
        warnings.append(
            f'sintetico.xlsx: falha ao ler {objetos_path}: {exc} — dados de'
            f'objetos '
            f"não anexados à aba '{_CAPA_SHEET_NAME}'"
        )
        return

    header_row = last_row + 2  # 1 linha em branco de separação
    objetos_columns = len(objetos_header)
    write_row(
        sheet,
        header_row,
        tuple(objetos_header),
        expected_columns=objetos_columns,
    )
    for row_idx, row in enumerate(objetos_rows, start=header_row + 1):
        write_row(sheet, row_idx, tuple(row), expected_columns=objetos_columns)
