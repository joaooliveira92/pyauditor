"""Aritmética de estatísticas de prazos do `sintetico.xlsx` (spec §14.4) —
**pura**, sem `openpyxl`.

Extraído de `excel/sintetico.py` (ticket 04 SRP): `_compute_stats` só conta
linhas/dentro/fora do prazo e o tempo médio criação→resolução sobre as linhas
aprovadas pelos quality gates. Nenhum formatador aqui sabe de células ou
workbooks — o renderer consome os valores já formatados.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

__all__: Final[tuple[str, ...]] = (
    "DATAHORA_FORMAT",
    "DATA_FIM",
    "DATA_SOLICITACAO",
    "NO_PRAZO_COLUMN",
    "NivelAccumulator",
    "Stats",
    "compute_stats",
    "fmt_pt_br",
    "format_duracao",
    "format_pct_bruto",
    "format_row",
    "parse_datahora",
)

NO_PRAZO_COLUMN: Final[str] = "No prazo"
DATA_SOLICITACAO: Final[str] = "DataHoraSolicitacao"
DATA_FIM: Final[str] = "DataHoraFim"
DATAHORA_FORMAT: Final[str] = "%d/%m/%Y %H:%M"


def parse_datahora(raw: str) -> datetime | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, DATAHORA_FORMAT)
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class Stats:
    linhas: int
    dentro: int | None
    fora: int | None
    duracao_total_segundos: float
    duracao_contagem: int


def compute_stats(
    rows: list[dict[str, str]], fieldnames: list[str], accepted_ids: set[int]
) -> Stats:
    dentro: int | None = None
    fora: int | None = None
    if NO_PRAZO_COLUMN in fieldnames:
        dentro = sum(1 for row in rows if row.get(NO_PRAZO_COLUMN) == "S")
        fora = sum(1 for row in rows if row.get(NO_PRAZO_COLUMN) == "N")

    duracao_total = 0.0
    duracao_contagem = 0
    if DATA_SOLICITACAO in fieldnames and DATA_FIM in fieldnames:
        for row in rows:
            if id(row) not in accepted_ids:
                continue
            inicio = parse_datahora(row.get(DATA_SOLICITACAO, ""))
            fim = parse_datahora(row.get(DATA_FIM, ""))
            if inicio is None or fim is None:
                continue
            duracao_total += (fim - inicio).total_seconds()
            duracao_contagem += 1

    return Stats(
        linhas=len(rows),
        dentro=dentro,
        fora=fora,
        duracao_total_segundos=duracao_total,
        duracao_contagem=duracao_contagem,
    )


def format_duracao(segundos: float) -> str:
    total_minutos = round(segundos / 60)
    dias, resto_minutos = divmod(total_minutos, 24 * 60)
    horas = resto_minutos // 60
    return f"{dias}d {horas:02d}h"


def fmt_pt_br(value: float, *, decimals: int = 1) -> str:
    """Separador decimal pt-BR (`,`) — mesma convenção de
    `orchestration/summary.py.fmt_pt_br`, duplicada aqui em miniatura pra
    `excel/` não depender de `orchestration/` (que por sua vez depende de
    `cli/split.py`, o chamador deste módulo — importar de volta ciclaria)."""
    return f"{value:.{decimals}f}".replace(".", ",")


def format_pct_bruto(dentro: int | None, fora: int | None) -> str:
    if dentro is None or fora is None or (dentro + fora) == 0:
        return "—"
    pct = dentro / (dentro + fora) * 100
    return f"{fmt_pt_br(pct)}%"


def format_row(stats: Stats) -> tuple[int, str | int, str | int, str, str]:
    dentro_display: str | int = stats.dentro if stats.dentro is not None else "—"
    fora_display: str | int = stats.fora if stats.fora is not None else "—"
    pct_display = format_pct_bruto(stats.dentro, stats.fora)
    tempo_display = (
        format_duracao(stats.duracao_total_segundos / stats.duracao_contagem)
        if stats.duracao_contagem > 0
        else "—"
    )
    return stats.linhas, dentro_display, fora_display, pct_display, tempo_display


@dataclass(frozen=True, slots=True)
class NivelAccumulator:
    linhas: int = 0
    dentro: int = 0
    fora: int = 0
    tem_prazo: bool = False
    duracao_total_segundos: float = 0.0
    duracao_contagem: int = 0

    def add(self, stats: Stats) -> NivelAccumulator:
        return NivelAccumulator(
            linhas=self.linhas + stats.linhas,
            dentro=self.dentro + (stats.dentro or 0),
            fora=self.fora + (stats.fora or 0),
            tem_prazo=self.tem_prazo or stats.dentro is not None,
            duracao_total_segundos=self.duracao_total_segundos + stats.duracao_total_segundos,
            duracao_contagem=self.duracao_contagem + stats.duracao_contagem,
        )
