"""Glosa monetária: item 35 do Termo de Referência, per docs/spec/inms-pipeline.md
§12. `Ajuste_NMS(%) = min(30%, Σ Pontos_NMS x 0,001%)`, valor da glosa =
percentual x valor-base, teto de 30% com rollover do excedente para o mês
seguinte (exceto no último mês de vigência do contrato).

Rollover e reincidência (`.scratch/framework-audit/issues/11-estado-persistente-
entre-competencias.md`) exigem estado entre execuções de `report` — o histórico
por órgão (`saldo_anterior_pct`/`houve_reincidencia`) é lido de
`roms/<orgao>/glosa_historico.json` pelo chamador (`cli/report.py`) e passado
aqui como dados puros, sem I/O nesta camada exceto `read_historico`/
`write_historico`.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pyauditor.atomic_write import atomic_write

POINTS_TO_PERCENT: Final = 0.001
CAP_PCT: Final = 30.0
JANELA_REINCIDENCIA_MESES: Final = 6
LIMITE_REINCIDENCIA: Final = 3


@dataclass(frozen=True)
class GlosaResult:
    total_points: float
    # Percentual bruto antes do teto de 30%, já somando o saldo rolado do mês
    # anterior — sempre igual a `percentual_ajuste + saldo_rolado_pct`.
    raw_pct: float
    percentual_ajuste: float
    teto_atingido: bool
    valor_base: float | None
    valor_da_glosa: float | None
    # Excedente além do teto de 30%, em pontos percentuais — 0 se o teto não
    # foi atingido, ou se é o último mês de vigência (não há mês seguinte).
    saldo_rolado_pct: float


def compute_glosa(
    total_points: float,
    valor_base: float | None,
    *,
    is_final_month: bool = False,
    saldo_anterior_pct: float = 0.0,
) -> GlosaResult:
    raw_pct = total_points * POINTS_TO_PERCENT + saldo_anterior_pct
    percentual_ajuste = min(raw_pct, CAP_PCT)
    teto_atingido = raw_pct > CAP_PCT

    saldo_rolado_pct = 0.0
    if teto_atingido and not is_final_month:
        saldo_rolado_pct = raw_pct - CAP_PCT

    valor_da_glosa = (percentual_ajuste / 100) * valor_base if valor_base is not None else None

    return GlosaResult(
        total_points=total_points,
        raw_pct=raw_pct,
        percentual_ajuste=percentual_ajuste,
        teto_atingido=teto_atingido,
        valor_base=valor_base,
        valor_da_glosa=valor_da_glosa,
        saldo_rolado_pct=saldo_rolado_pct,
    )


def competencia_anterior(competencia: str) -> str:
    """`"2026-01"` -> `"2025-12"`; `"2026-07"` -> `"2026-06"`."""
    ano, mes = (int(parte) for parte in competencia.split("-"))
    if mes == 1:
        return f"{ano - 1}-12"
    return f"{ano}-{mes - 1:02d}"


def janela_reincidencia(competencia: str) -> list[str]:
    """As `JANELA_REINCIDENCIA_MESES` competências terminando em `competencia`
    (inclusive), da mais recente para a mais antiga.
    """
    janela = [competencia]
    atual = competencia
    for _ in range(JANELA_REINCIDENCIA_MESES - 1):
        atual = competencia_anterior(atual)
        janela.append(atual)
    return janela


Historico = dict[str, dict[str, object]]


def saldo_anterior_pct_de(historico: Historico, competencia: str) -> float:
    """`saldo_rolado_pct` da competência imediatamente anterior, ou 0.0 se
    não houver registro (primeira competência, ou mês anterior pulado).
    """
    entry = historico.get(competencia_anterior(competencia))
    if entry is None:
        return 0.0
    value = entry.get("saldo_rolado_pct")
    return float(value) if isinstance(value, int | float) else 0.0


def houve_reincidencia(
    historico: Historico, competencia: str, teto_atingido_mes_atual: bool
) -> bool:
    """Item 35 do TR: teto de 30% estourado 3+ vezes em 6 meses caracteriza
    inexecução parcial do contrato — flag de compliance, não altera o valor
    da glosa (ver `.scratch/framework-audit/issues/03-reincidencia-nao-
    rastreada.md`).
    """
    ocorrencias = 1 if teto_atingido_mes_atual else 0
    for c in janela_reincidencia(competencia)[1:]:
        entry = historico.get(c)
        if entry is not None and bool(entry.get("teto_atingido")):
            ocorrencias += 1
    return ocorrencias >= LIMITE_REINCIDENCIA


def read_historico(path: Path) -> Historico:
    if not path.exists():
        return {}
    return dict(json.loads(path.read_text(encoding="utf-8")))


def write_historico(path: Path, historico: Historico) -> None:
    payload = json.dumps(historico, indent=2, sort_keys=True, ensure_ascii=False)
    atomic_write(path, lambda tmp: tmp.write_text(payload, encoding="utf-8"))


def historico_entry(competencia: str, glosa: GlosaResult) -> dict[str, object]:
    return {
        "total_points": glosa.total_points,
        "raw_pct": glosa.raw_pct,
        "percentual_ajuste": glosa.percentual_ajuste,
        "teto_atingido": glosa.teto_atingido,
        "saldo_rolado_pct": glosa.saldo_rolado_pct,
    }
