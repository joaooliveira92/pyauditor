"""Aritmética pura da aba `CALCULO_PAGAMENTO` (ticket 03 SRP) — **sem**
`openpyxl`.

Extraído de `excel/consolidate/workbook.py` (`build_calculo`): as linhas da
planilha (rateio, valor bruto, pontos de glosa, valor da glosa, outros ajustes
e valor recomendado) são derivadas daqui como valores; o builder apenas
escreve células e aplica formato. Nenhuma célula nasce neste módulo.
"""

from __future__ import annotations

from dataclasses import dataclass

from pyauditor.excel.glosas import compute_glosa

__all__: tuple[str, ...] = (
    'CalculoRowValues',
    'compute_calculo_row',
    'glosa_valor_sobre_bruto',
)


def glosa_valor_sobre_bruto(pontos: float, bruto: float) -> float:
    """Valor da glosa sobre um bruto — a mesma aritmética de
    ``glosas.compute_glosa`` (fonte única, ticket 09), sem rollover
    (``is_final_month=True``) porque as células de ``CALCULO_PAGAMENTO``
    computam o ajuste do mês corrente, não o saldo rolado.
    """
    glosa = compute_glosa(pontos, bruto, is_final_month=True)
    return glosa.valor_da_glosa or 0.0


@dataclass(frozen=True)
class CalculoRowValues:
    """Os valores da linha de um órgão/coluna da aba ``CALCULO_PAGAMENTO``,
    na ordem das linhas de ``workbook._CALCULO_LINHAS``."""

    percentual_rateio: float
    valor_bruto: float
    pontos_glosa: float
    valor_glosa: float
    outros_ajustes: float
    valor_recomendado: float


def compute_calculo_row(
    *,
    rateio: float,
    base: float,
    pontos: float,
) -> CalculoRowValues:
    """Deriva a linha de pagamento de uma coluna (órgão ou consolidado).

    `base` é o valor mensal vigente **já normalizado** (``valor_base or 0.0``
    aplicado pelo builder). ``valor_recomendado`` é
    ``max(0, bruto - glosa - outros)`` com a glosa **não** arredondada (a
    coluna exibe o arredondamento a 2 casas).
    """
    bruto = round(base * rateio, 2)
    glosa = glosa_valor_sobre_bruto(pontos, bruto)
    valor_glosa = round(glosa, 2)
    outros_ajustes = 0.0
    return CalculoRowValues(
        percentual_rateio=rateio,
        valor_bruto=bruto,
        pontos_glosa=round(pontos, 2),
        valor_glosa=valor_glosa,
        outros_ajustes=outros_ajustes,
        valor_recomendado=round(max(0.0, bruto - glosa - outros_ajustes), 2),
    )
