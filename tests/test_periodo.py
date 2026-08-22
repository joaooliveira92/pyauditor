"""Unit tests for `pyauditor.periodo` (spec: .scratch/competencia-cli-equipe,
§1 derivação do período, §2 filtro puro, §3 política de linhas)."""

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from pyauditor.periodo import (
    PeriodoAfericao,
    discard_message,
    empty_window_message,
    filter_periodo,
    format_date_br,
    format_period_br,
    month_bounds,
    require_period_column,
)

COLUNA = "Data da medição"


def _linha(valor: str) -> dict[str, str]:
    return {COLUNA: valor, "Grupo_executor": "G1"}


class TestMesBounds:
    def test_mes_simples(self) -> None:
        assert month_bounds("2026-06") == PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))

    def test_dezembro_fecha_no_ultimo_dia_do_ano(self) -> None:
        assert month_bounds("2025-12") == PeriodoAfericao(date(2025, 12, 1), date(2025, 12, 31))

    def test_fevereiro_bissexto(self) -> None:
        assert month_bounds("2024-02").fim == date(2024, 2, 29)

    def test_fevereiro_nao_bissexto(self) -> None:
        assert month_bounds("2025-02").fim == date(2025, 2, 28)

    @pytest.mark.parametrize(
        "competencia",
        ["2026-13", "2026-00", "2026-6", "junho", "", "202606", "2026-06-extra"],
    )
    def test_formatos_invalidos_erro_acionavel(self, competencia: str) -> None:
        with pytest.raises(ValueError, match="AAAA-MM"):
            month_bounds(competencia)

    def test_periodo_imutavel(self) -> None:
        periodo = month_bounds("2026-06")
        with pytest.raises(FrozenInstanceError):
            periodo.inicio = date(2026, 7, 1)  # type: ignore[misc]


class TestFilterPeriodo:
    JUNHO = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))

    def test_mistos_mantem_janela_e_conta_descartes(self) -> None:
        linhas = [_linha("05/06/2026 14:33"), _linha("10/07/2026 09:00")]
        resultado = filter_periodo(linhas, period_column=COLUNA, periodo=self.JUNHO)
        assert resultado.linhas_na_janela == [_linha("05/06/2026 14:33")]
        assert resultado.dropped_out_of_period == 1
        assert resultado.undated_dropped == 0

    def test_formato_mes_yyyy_mm(self) -> None:
        linhas = [_linha("2026-06"), _linha("2026-08")]
        resultado = filter_periodo(linhas, period_column=COLUNA, periodo=self.JUNHO)
        assert [linha[COLUNA] for linha in resultado.linhas_na_janela] == ["2026-06"]
        assert resultado.dropped_out_of_period == 1

    def test_limites_da_janela(self) -> None:
        linhas = [
            _linha("01/06/2026 00:00"),
            _linha("30/06/2026 23:59"),
            _linha("01/07/2026 00:00"),
        ]
        resultado = filter_periodo(linhas, period_column=COLUNA, periodo=self.JUNHO)
        assert len(resultado.linhas_na_janela) == 2
        assert resultado.dropped_out_of_period == 1

    @pytest.mark.parametrize("valor", ["", "   ", "ontem", "2026/06", "2026-06-15"])
    def test_sem_data_legivel_default_segue_para_gates(self, valor: str) -> None:
        linhas = [_linha("05/06/2026 08:00"), _linha(valor)]
        resultado = filter_periodo(linhas, period_column=COLUNA, periodo=self.JUNHO)
        assert len(resultado.linhas_na_janela) == 2
        assert resultado.undated_dropped == 0

    @pytest.mark.parametrize("valor", ["", "   ", "ontem", "2026/06", "2026-06-15"])
    def test_sem_data_legivel_strict_descarta_e_conta(self, valor: str) -> None:
        linhas = [_linha("05/06/2026 08:00"), _linha(valor)]
        resultado = filter_periodo(linhas, period_column=COLUNA, periodo=self.JUNHO, strict=True)
        assert len(resultado.linhas_na_janela) == 1
        assert resultado.undated_dropped == 1
        assert resultado.dropped_out_of_period == 0

    def test_coluna_chave_ausente_tratada_como_sem_data(self) -> None:
        linhas: list[dict[str, str]] = [{"Grupo_executor": "G1"}]
        default = filter_periodo(linhas, period_column=COLUNA, periodo=self.JUNHO)
        assert len(default.linhas_na_janela) == 1
        strict = filter_periodo(linhas, period_column=COLUNA, periodo=self.JUNHO, strict=True)
        assert strict.linhas_na_janela == []
        assert strict.undated_dropped == 1

    def test_dataset_vazio_estado_legitimo_preservado(self) -> None:
        linhas: list[dict[str, str]] = []
        resultado = filter_periodo(linhas, period_column=COLUNA, periodo=self.JUNHO, strict=True)
        assert resultado.linhas_na_janela == []
        assert resultado.dropped_out_of_period == 0
        assert resultado.undated_dropped == 0

    def test_refiltro_e_idempotente(self) -> None:
        linhas = [_linha("05/06/2026 14:33"), _linha("10/07/2026 09:00")]
        primeira = filter_periodo(linhas, period_column=COLUNA, periodo=self.JUNHO)
        segunda = filter_periodo(
            primeira.linhas_na_janela, period_column=COLUNA, periodo=self.JUNHO
        )
        assert segunda.linhas_na_janela == primeira.linhas_na_janela
        assert segunda.dropped_out_of_period == 0
        assert segunda.undated_dropped == 0

    def test_entrada_nao_e_mutada(self) -> None:
        linhas = [_linha("05/06/2026 14:33"), _linha("10/07/2026 09:00")]
        filter_periodo(linhas, period_column=COLUNA, periodo=self.JUNHO)
        assert len(linhas) == 2


class TestRequirePeriodColumn:
    def test_retorna_coluna_quando_declarada(self) -> None:
        assert require_period_column("Data da medição", config_path="x.yaml") == "Data da medição"

    def test_erro_cita_o_yaml(self) -> None:
        with pytest.raises(ValueError, match=r"inms-07\.yaml"):
            require_period_column(None, config_path="input/minc/inms-07.yaml")

    def test_erro_sem_yaml_conhecido(self) -> None:
        with pytest.raises(ValueError, match=r"source\.period_column"):
            require_period_column("", config_path=None)


class TestMensagens:
    JUNHO = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))

    def test_format_date_br_preenche_zero(self) -> None:
        assert format_date_br(date(2026, 6, 1)) == "01/06/2026"

    def test_format_period_br(self) -> None:
        assert format_period_br(self.JUNHO) == "01/06/2026 a 30/06/2026"

    def test_empty_window_message(self) -> None:
        assert empty_window_message(self.JUNHO) == (
            "nenhuma linha no período 01/06/2026–30/06/2026 — o arquivo corresponde à competência?"
        )

    def test_discard_message_somente_fora(self) -> None:
        assert discard_message(3, 0, strict=False) == "3 linha(s) fora do período descartada(s)"

    def test_discard_message_fora_e_sem_data_sob_strict(self) -> None:
        assert discard_message(5, 2, strict=True) == (
            "5 linha(s) fora do período descartada(s) e 2 sem data legível"
        )

    def test_discard_message_so_sem_data_sob_strict(self) -> None:
        assert discard_message(0, 4, strict=True) == "4 linha(s) sem data legível descartada(s)"

    def test_discard_message_nada_a_relatar(self) -> None:
        assert discard_message(0, 0, strict=False) is None
        assert discard_message(0, 3, strict=False) is None
