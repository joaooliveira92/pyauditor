"""Ponto de entrada das abas institucionais de `sintetico.xlsx`
(Capa/Equipe/Prazos/Localidades/Sansões). Cada aba tem seu próprio renderer
em `_sheets/<aba>.py` (`capa.py`, `equipe.py`, `prazos.py`, `localidades.py`,
`sancoes.py`); este módulo só orquestra a ordem de geração — título e
subtítulo das demais abas referenciam a Capa por fórmula (`=Capa!B2`), nunca
por segunda digitação independente.
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from pyauditor.excel.sintetico._sheets._shared import (
    CAPA_SHEET_NAME,
    CapaContext,
)
from pyauditor.excel.sintetico._sheets.capa import write_capa_sheet
from pyauditor.excel.sintetico._sheets.equipe import write_equipe_sheet
from pyauditor.excel.sintetico._sheets.localidades import (
    _write_localidades_sheet,
)
from pyauditor.excel.sintetico._sheets.prazos import write_prazos_sheet
from pyauditor.excel.sintetico._sheets.sancoes import _write_sancoes_sheet


def write_institutional_sheets(
    workbook: Workbook,
    *,
    capa_path: Path | None,
    dados_contratuais_path: Path | None = None,
    objetos_path: Path | None,
    equipe_path: Path | None,
    perfis_profissionais_path: Path | None = None,
    prazos_path: Path | None,
    localidades_path: Path | None = None,
    warnings: list[str],
) -> None:
    """Ponto de entrada usado por `sintetico/workbook.py`: gera Capa/Equipe/
    Prazos/Localidades/Sansões formatadas, nessa ordem — título e
    subtítulo delas referenciam a Capa por fórmula (`=Capa!B2`), nunca por
    segunda digitação independente."""
    contexto = CapaContext(None)
    if capa_path is not None:
        contexto = write_capa_sheet(
            workbook,
            capa_path,
            dados_contratuais_path,
            objetos_path,
            warnings,
        )
    elif objetos_path is not None:
        warnings.append(
            f'sintetico.xlsx: capa_path não informado — dados de '
            f'{objetos_path} não anexados (dependem da aba '
            f"'{CAPA_SHEET_NAME}')"
        )

    if equipe_path is not None:
        write_equipe_sheet(
            workbook,
            equipe_path,
            perfis_profissionais_path,
            contexto.numero_contrato,
            warnings,
        )

    if prazos_path is not None:
        write_prazos_sheet(
            workbook, prazos_path, contexto.numero_contrato, warnings
        )

    if localidades_path is not None:
        _write_localidades_sheet(
            workbook, localidades_path, contexto.numero_contrato, warnings
        )

    _write_sancoes_sheet(workbook, contexto.numero_contrato, warnings)
