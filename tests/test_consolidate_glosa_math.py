"""Unidade da matemática financeira de `excel/consolidate/` (tickets 01
rede-testes e 03 SRP): os helpers puros `glosa_valor_sobre_bruto` e
`faixa_descumprimento` (vivem nos módulos de matemática, não no builder),
a agregação determinística de `_glosa_calcs` e o cálculo da aba
`CALCULO_PAGAMENTO` — o rateio MinC/MTur e a linha da glosa — travados com
valores esperados concretos.

Inclui a regressão da linha "Valor da glosa" (o refactor SRP anterior
removeu o espaço da label `Valordaglosa(...)`, fazendo a linha cair no ramo
de "Valor recomendado" e exibir `bruto - glosa` no lugar da glosa). O teste
abaixo trava o valor correto após a restauração da label.
"""

from datetime import date

import pytest
from openpyxl import Workbook

from pyauditor.excel.consolidate._calculo_calcs import glosa_valor_sobre_bruto
from pyauditor.excel.consolidate._glosa_calcs import (
    compute_aggregation,
    faixa_descumprimento,
)
from pyauditor.excel.consolidate.workbook import (
    CALCULO_SHEET,
    _decision_value,
    build_calculo,
)
from pyauditor.rom.summary import IndicatorSummary


def _fresh_workbook() -> Workbook:
    wb = Workbook()
    default = wb.active
    assert default is not None
    wb.remove(default)
    return wb


def _summary(
    contractual_id: str,
    *,
    target_operator: str | None = '>=',
    target_value: float | None = 98.0,
    result_pct: float = 97.5,
    penalty_points: float = 0.0,
) -> IndicatorSummary:
    return IndicatorSummary(
        indicator_id=f'{contractual_id}-IND',
        contractual_id=contractual_id,
        name=f'Indicador {contractual_id}',
        asset=None,
        orgao='MinC',
        shape='ratio',
        target_operator=target_operator,
        target_value=target_value,
        result_pct=result_pct,
        conforms=result_pct >= (target_value or 0.0),
        penalty_points=penalty_points,
        numerator=1,
        denominator=2,
        hard_failure=False,
    )


def _calculo_rows(
    wb: Workbook,
    valor_base: float | None,
    total_pontos: float,
    *,
    rateio: float = 0.5,
) -> dict[str, list[object]]:
    build_calculo(
        wb,
        valor_base,
        total_pontos,
        rateio_minc=rateio,
        rateio_mtur=rateio,
    )
    ws = wb[CALCULO_SHEET]
    rows: dict[str, list[object]] = {}
    for r in range(10, 16):
        label = ws.cell(row=r, column=1).value
        if label is None:
            continue
        rows[str(label)] = [ws.cell(row=r, column=c).value for c in range(2, 5)]
    return rows


class TestGlosaBruto:
    def test_below_cap(self) -> None:
        assert glosa_valor_sobre_bruto(1000.0, 100_000.0) == pytest.approx(
            1000.0
        )

    def test_above_cap_is_capped_without_rollover(self) -> None:
        assert glosa_valor_sobre_bruto(40_000.0, 100_000.0) == pytest.approx(
            30_000.0
        )

    def test_zero_pontos(self) -> None:
        assert glosa_valor_sobre_bruto(0.0, 50_000.0) == pytest.approx(0.0)

    def test_per_orgao_bruto_partial(self) -> None:
        assert glosa_valor_sobre_bruto(150.0, 100_000.0) == pytest.approx(150.0)


class TestFaixa:
    def test_ge_operator_directs_deficit(self) -> None:
        summary = _summary(
            'INMS 1.1', target_operator='>=', target_value=98.0, result_pct=97.5
        )
        assert faixa_descumprimento(summary) == 'Déficit de 0.50pp'

    def test_ge_operator_met_is_nao_conforme(self) -> None:
        summary = _summary(
            'INMS 1.1', target_operator='>=', target_value=98.0, result_pct=98.5
        )
        assert faixa_descumprimento(summary) == 'Não conforme'

    def test_le_operator_inverts_deficit_direction(self) -> None:
        summary = _summary(
            'INMS 1.6', target_operator='<=', target_value=2.0, result_pct=2.5
        )
        assert faixa_descumprimento(summary) == 'Déficit de 0.50pp'

    def test_asset_detail_with_breach(self) -> None:
        summary = _summary(
            'INMS 1.14',
            target_operator=None,
            target_value=None,
            penalty_points=50.0,
        )
        assert (
            faixa_descumprimento(summary)
            == 'Ocorrência sob detalhamento por-ativo'
        )

    def test_asset_detail_without_breach(self) -> None:
        summary = _summary('INMS 1.14', target_operator=None, target_value=None)
        assert faixa_descumprimento(summary) == ''


class TestDecisionValue:
    def test_missing_key_is_none(self) -> None:
        assert _decision_value({}, 'Decisão Fiscal') is None

    def test_scalars_pass_through(self) -> None:
        for value in ('Aceita', 7, 7.5, True):
            assert _decision_value({'k': value}, 'k') == value

    def test_non_scalar_is_coerced_to_string(self) -> None:
        assert _decision_value({'k': date(2026, 6, 1)}, 'k') == '2026-06-01'
        assert _decision_value({'k': ['a']}, 'k') == "['a']"


class TestComputeAggregation:
    def test_rateia_saldo_anterior_por_pontos_e_soma_glosas(self) -> None:
        resultado = compute_aggregation(
            pontos_por_orgao={'MinC': 100.0, 'MTur': 200.0},
            valor_base=10_000.0,
            competencia='2026-06',
            historico={'2026-05': {'saldo_rolado_pct': 15.0}},
            is_final_month=False,
        )
        # Saldo 15 pp rateado: MinC 5.0, MTur 10.0 (proporcional aos pontos).
        assert resultado.total_pontos == pytest.approx(300.0)
        assert resultado.glosa_final == pytest.approx(1530.0)
        assert resultado.pct_bruto == pytest.approx(15.3)
        assert resultado.aplicado == pytest.approx(15.3)

    def test_zero_pontos_nao_rateia_saldo(self) -> None:
        resultado = compute_aggregation(
            pontos_por_orgao={'MinC': 0.0, 'MTur': 0.0},
            valor_base=10_000.0,
            competencia='2026-06',
            historico={'2026-05': {'saldo_rolado_pct': 15.0}},
            is_final_month=False,
        )
        assert resultado.total_pontos == 0.0
        assert resultado.glosa_final == 0.0
        assert resultado.pct_bruto == pytest.approx(15.0)

    def test_teto_de_30_aplicado_no_agregado(self) -> None:
        resultado = compute_aggregation(
            pontos_por_orgao={'MinC': 40_000.0, 'MTur': 0.0},
            valor_base=10_000.0,
            competencia='2026-06',
            historico=None,
            is_final_month=False,
        )
        assert resultado.pct_bruto == pytest.approx(40.0)
        assert resultado.aplicado == pytest.approx(30.0)
        assert resultado.glosa_final == pytest.approx(3000.0)


class TestBuildCalculo:
    def test_rateio_minc_mtur_e_linha_da_glosa(self) -> None:
        wb = _fresh_workbook()
        rows = _calculo_rows(wb, 100_000.0, 150.0, rateio=0.5)

        assert rows['Percentual de rateio'] == [0.5, 0.5, 1.0]
        assert rows['Valor bruto (= mensal x rateio)'] == [
            50_000.0,
            50_000.0,
            100_000.0,
        ]
        assert rows['Pontos de glosa'] == [0.0, 0.0, 150.0]
        assert rows['Outros ajustes'] == [0, 0, 0]
        assert rows['Valor recomendado (= max(0, bruto - glosa - outros))'] == [
            50_000.0,
            50_000.0,
            99_850.0,
        ]

    def test_glosa_row_holds_glosa_not_remaining(self) -> None:
        """Regressão (refactor SRP anterior): a label `Valordaglosa(...)` sem
        espaço quebrava `startswith('Valor da glosa')` e a linha exibia
        `bruto - glosa` no lugar da glosa."""
        wb = _fresh_workbook()
        rows = _calculo_rows(wb, 100_000.0, 150.0, rateio=0.5)

        glosa_row = [
            label for label in rows if label.startswith('Valor da glosa')
        ]
        assert glosa_row, 'linha "Valor da glosa" ausente'
        assert rows[glosa_row[0]] == [0.0, 0.0, 150.0]

    def test_valor_base_none_zeroes_money_but_keeps_pontos(self) -> None:
        wb = _fresh_workbook()
        rows = _calculo_rows(wb, None, 150.0, rateio=0.5)

        assert rows['Pontos de glosa'] == [0.0, 0.0, 150.0]
        glosa_row = [
            label for label in rows if label.startswith('Valor da glosa')
        ]
        assert rows[glosa_row[0]] == [0.0, 0.0, 0.0]
        assert rows['Valor bruto (= mensal x rateio)'] == [0.0, 0.0, 0.0]
