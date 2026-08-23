"""Rede de segurança da resolução de categorias (reducao-friccao, ticket 01).

Testes unitários puros das funções de `pyauditor/categoria_filter.py`, sem
tocar em CSV nem em CLI: travam o comportamento atual de
`compute_categoria_values`, `unmatched_in_values_warnings`, `outros_warning`
e `base_config_stem` antes dos refactors dos tickets 04/05.

Cada valor esperado é literal determinístico do comportamento atual, não
golden opaco re-derivado da implementação.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pytest

from pyauditor.categoria_filter import (
    base_config_stem,
    compute_categoria_values,
    outros_warning,
    unmatched_in_values_warnings,
)
from pyauditor.config.categorias import GrupoExecutorMode

_FAKE_CSV_PATH: Final = Path('/data/inms-01.csv')


def _in_values(*values: str) -> GrupoExecutorMode:
    return GrupoExecutorMode(mode='grupo_executor', in_values=list(values))


def _catch_all(contains: str) -> GrupoExecutorMode:
    return GrupoExecutorMode(mode='grupo_executor', catch_all_contains=contains)


class TestComputeCategoriaValues:
    """Resolução de valores de `Grupo_executor` por categoria."""

    def test_in_values_atribui_exatamente_os_valores_listados(self) -> None:
        result = compute_categoria_values(
            [('ATENDIMENTO_N1', _in_values('N1', 'N2'))],
            real_values={'N1', 'N2', 'N3'},
        )

        per_categoria, outros = result
        assert per_categoria == {'ATENDIMENTO_N1': {'N1', 'N2'}}
        assert outros == {'N3'}

    def test_catch_all_exclui_valor_ja_reivindicado_por_in_values(
        self,
    ) -> None:
        """`catch_all_contains` nunca devolve um valor que um `in_values`
        de outra categoria do mesmo INMS já reivindicou (nenhuma linha pode
        pertencer a duas categorias)."""
        result = compute_categoria_values(
            [
                ('ATENDIMENTO_N1', _in_values('(CIT) - N1')),
                ('OPERACAO_N3', _catch_all('(CIT)')),
            ],
            real_values={'(CIT) - N1', '(CIT) - N2', 'N3'},
        )

        per_categoria, outros = result
        assert per_categoria == {
            'ATENDIMENTO_N1': {'(CIT) - N1'},
            'OPERACAO_N3': {'(CIT) - N2'},
        }
        assert outros == {'N3'}

    def test_catch_all_substring_requer_parenteses_fechando(self) -> None:
        """`catch_all_contains` casa por substring literal: `(CIT)` (com a
        `)`) casa `(CIT) - Infra`, mas não `(CIT/MINC) - 2º Nível`."""
        result = compute_categoria_values(
            [('OPERACAO_N3', _catch_all('(CIT)'))],
            real_values={'(CIT) - Infra', '(CIT/MINC) - 2º Nível', 'N3'},
        )

        per_categoria, outros = result
        assert per_categoria == {'OPERACAO_N3': {'(CIT) - Infra'}}
        assert outros == {'N3', '(CIT/MINC) - 2º Nível'}

    def test_in_values_nao_depende_dos_valores_reais(self) -> None:
        """`in_values` reivindica os literais mesmo quando nenhum aparece no
        CSV (o descompasso é reportado por `unmatched_in_values_warnings`,
        não aqui)."""
        result = compute_categoria_values(
            [('ATENDIMENTO_N1', _in_values('N1'))],
            real_values=set(),
        )

        per_categoria, outros = result
        assert per_categoria == {'ATENDIMENTO_N1': {'N1'}}
        assert outros == set()

    def test_mesmo_valor_de_in_values_em_duas_categorias_raise(self) -> None:
        with pytest.raises(ValueError, match='aparece em mais de uma'):
            compute_categoria_values(
                [
                    ('ATENDIMENTO_N1', _in_values('N1')),
                    ('ATENDIMENTO_N2', _in_values('N1')),
                ],
                real_values={'N1', 'N2'},
            )

    def test_in_values_preempta_catch_all_em_qualquer_ordem(self) -> None:
        """A exclusão de `in_values` vale para todo o INMS, não só para
        categorias anteriores: o `catch_all` vem primeiro mas desiste do
        valor que o `in_values` da categoria seguinte reivindica."""
        result = compute_categoria_values(
            [
                ('OPERACAO_N3', _catch_all('(CIT)')),
                ('ATENDIMENTO_N1', _in_values('(CIT) - Infra')),
            ],
            real_values={'(CIT) - Infra', '(CIT) - N2'},
        )

        per_categoria, outros = result
        assert per_categoria == {
            'OPERACAO_N3': {'(CIT) - N2'},
            'ATENDIMENTO_N1': {'(CIT) - Infra'},
        }
        assert outros == set()

    def test_dois_catch_all_sobrepostos_raise(self) -> None:
        """Dois `catch_all_contains` que casam o mesmo valor real (ex.:
        `(CIT)` e `CIT`) são sobreposição: a linha seria contada duas
        vezes (único caso de sobreposição que a exclusão de `in_values` não
        absorve)."""
        with pytest.raises(
            ValueError, match='sobrepõe valores já reivindicados'
        ):
            compute_categoria_values(
                [
                    ('ATENDIMENTO_N1', _catch_all('(CIT)')),
                    ('ATENDIMENTO_N2', _catch_all('CIT')),
                ],
                real_values={'(CIT) - Infra'},
            )


class TestUnmatchedInValuesWarnings:
    def _warnings(
        self, entries: list[tuple[str, GrupoExecutorMode]]
    ) -> list[str]:
        return unmatched_in_values_warnings(
            inms_key='1.1',
            orgao='MinC',
            competencia='2026-06',
            entries=entries,
            real_values={'N1', 'N2'},
            raw_csv_path=_FAKE_CSV_PATH,
        )

    def test_todos_os_in_values_presentes_nao_gera_aviso(self) -> None:
        warnings = self._warnings([('ATENDIMENTO_N1', _in_values('N1'))])

        assert warnings == []

    def test_in_values_totalmente_ausente_avisa_possivel_typo(self) -> None:
        warnings = self._warnings([('ATENDIMENTO_N1', _in_values('N0'))])

        assert warnings == [
            'INMS 1.1 (MinC/2026-06), categoria ATENDIMENTO_N1: in_values '
            "['N0'] sem correspondência em Grupo_executor do CSV "
            '(/data/inms-01.csv) — possível typo/renomeação, categoria '
            'ficará sem linhas'
        ]

    def test_in_values_parcial_avisa_sem_typo(self) -> None:
        """Pelo menos um valor bateu: o aviso deixa de sugerir typo e só
        lista os não encontrados."""
        warnings = self._warnings([('ATENDIMENTO_N1', _in_values('N1', 'N0'))])

        assert warnings == [
            'INMS 1.1 (MinC/2026-06), categoria ATENDIMENTO_N1: in_values '
            "['N0'] sem correspondência — valores não encontrados no CSV"
        ]

    def test_entrada_catch_all_nao_gera_aviso(self) -> None:
        warnings = self._warnings([('OPERACAO_N3', _catch_all('(CIT)'))])

        assert warnings == []


def test_outros_warning_conta_linhas_e_ordem_revisar() -> None:
    message = outros_warning(
        inms_key='1.1', orgao='MinC', competencia='2026-06', outros_count=5
    )

    assert message == (
        'INMS 1.1 (MinC/2026-06), categoria outros: 5 linha(s) não '
        'classificada(s) em nenhuma categoria — revisar categorias.yaml'
    )


@pytest.mark.parametrize(
    ('inms_key', 'expected_stem'),
    [('1.1', 'inms-01'), ('1.9', 'inms-09'), ('1.14', 'inms-14')],
)
def test_base_config_stem_zero_padded_two_digits(
    inms_key: str, expected_stem: str
) -> None:
    assert base_config_stem(inms_key) == expected_stem


@pytest.mark.parametrize(
    'inms_key',
    ['abc', '1', '2.1', '1.', '1.1.1', '01.1', '1. 2'],
)
def test_base_config_stem_chave_invalida_raise(inms_key: str) -> None:
    with pytest.raises(ValueError, match=r"esperado '1\.<n>'") as exc_info:
        base_config_stem(inms_key)
    assert inms_key in str(exc_info.value)
