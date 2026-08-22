"""Derivação da janela de aferição e filtro puro de período (spec:
.scratch/competencia-cli-equipe §1-§3).

Fonte única de Competência/Período é o argumento posicional obrigatório da
CLI — nada lê esses valores da capa nem infere dos dados. O filtro aqui é
uma função pura: devolve contagens e a lista pós-janela; quem chama loga.
"""

import calendar
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import NamedTuple

# Os dois formatos de célula conhecidos, disjuntos (§2): timestamp do dataset
# e mês compacto. Qualquer outro valor = linha sem data legível.
_DATETIME_CELL_FORMAT = "%d/%m/%Y %H:%M"
_MONTH_CELL_RE = re.compile(r"\d{4}-\d{2}")
_COMPETENCIA_RE = re.compile(r"\d{4}-(0[1-9]|1[0-2])")


@dataclass(frozen=True)
class PeriodoAfericao:
    """Janela fechada [inicio, fim] derivada exclusivamente da CLI."""

    inicio: date
    fim: date


class PeriodColumnMissingError(ValueError):
    """YAML sem `source.period_column` num fluxo que passou um período."""


def month_bounds(competencia: str) -> PeriodoAfericao:
    """`'2026-06'` → 01/06/2026..30/06/2026; `'2025-12'` fecha em 31/12."""
    if not _COMPETENCIA_RE.fullmatch(competencia):
        raise ValueError(f"competência inválida: {competencia!r} — esperado AAAA-MM (mês 01-12)")
    ano, mes = int(competencia[:4]), int(competencia[5:7])
    inicio = date(ano, mes, 1)
    fim = date(ano, mes, calendar.monthrange(ano, mes)[1])
    return PeriodoAfericao(inicio, fim)


def require_period_column(
    period_column: str | None,
    *,
    config_path: Path | str | None = None,
) -> str:
    """Obrigatoriedade na execução (§2): fluxo real passa um período; YAML sem
    coluna declarada é erro acionável apontando o arquivo."""
    coluna = (period_column or "").strip()
    if coluna:
        return coluna
    origem = f" em {config_path}" if config_path else ""
    raise PeriodColumnMissingError(
        f"source.period_column não declarado{origem} — indique a coluna de período do "
        "dataset no YAML para o pipeline filtrar pela janela da competência"
    )


def _cell_interval(valor_celula: str | None) -> tuple[date, date] | None:
    """Inferência entre os dois formatos conhecidos → intervalo coberto pela
    célula; `None` quando vazia/ilegível (linha "sem data")."""
    texto = (valor_celula or "").strip()
    if not texto:
        return None
    try:
        momento = datetime.strptime(texto, _DATETIME_CELL_FORMAT)
    except ValueError:
        pass
    else:
        dia = momento.date()
        return dia, dia
    if _MONTH_CELL_RE.fullmatch(texto):
        try:
            primeiro = date(int(texto[:4]), int(texto[5:7]), 1)
        except ValueError:
            return None
        ultimo_dia = calendar.monthrange(primeiro.year, primeiro.month)[1]
        return primeiro, date(primeiro.year, primeiro.month, ultimo_dia)
    return None


class PeriodFilterResult(NamedTuple):
    linhas_na_janela: list[dict[str, str]]
    dropped_out_of_period: int
    undated_dropped: int


def filter_periodo(
    linhas: Sequence[dict[str, str]],
    *,
    period_column: str,
    periodo: PeriodoAfericao,
    strict: bool = False,
) -> PeriodFilterResult:
    """Filtro puro (§3): mantém linhas dentro da janela; data legível fora é
    sempre descartada; célula sem data segue para quality gates no default e
    é descartada sob `--strict`. Re-filtrar é idempotente."""
    na_janela: list[dict[str, str]] = []
    dropped_out_of_period = 0
    undated_dropped = 0
    for linha in linhas:
        intervalo = _cell_interval(linha.get(period_column))
        if intervalo is None:
            if strict:
                undated_dropped += 1
            else:
                na_janela.append(linha)
            continue
        dentro = intervalo[1] >= periodo.inicio and intervalo[0] <= periodo.fim
        if dentro:
            na_janela.append(linha)
        else:
            dropped_out_of_period += 1
    return PeriodFilterResult(na_janela, dropped_out_of_period, undated_dropped)


def format_date_br(data: date) -> str:
    return f"{data.day:02d}/{data.month:02d}/{data.year}"


def format_period_br(periodo: PeriodoAfericao) -> str:
    """Formato canônico de exibição: `01/06/2026 a 30/06/2026`."""
    return f"{format_date_br(periodo.inicio)} a {format_date_br(periodo.fim)}"


def empty_window_message(periodo: PeriodoAfericao) -> str:
    """Texto aprovado no spec §3 — verbatim, incluindo o en-dash."""
    return (
        f"nenhuma linha no período {format_date_br(periodo.inicio)}–"
        f"{format_date_br(periodo.fim)} — o arquivo corresponde à competência?"
    )


def discard_message(dropped_out_of_period: int, undated_dropped: int, strict: bool) -> str | None:
    """INFO de dataset misto (§3); `None` quando nada há a relatar."""
    partes: list[str] = []
    if dropped_out_of_period > 0:
        partes.append(f"{dropped_out_of_period} linha(s) fora do período descartada(s)")
    if strict and undated_dropped > 0:
        if partes:
            partes.append(f"{undated_dropped} sem data legível")
        else:
            partes.append(f"{undated_dropped} linha(s) sem data legível descartada(s)")
    if not partes:
        return None
    return " e ".join(partes)
