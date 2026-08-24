from __future__ import annotations

from pathlib import Path

from pyauditor.categoria_filter import (
    Warning,
    outros_warning,
    unmatched_in_values_warnings,
)
from pyauditor.config.categorias import GrupoExecutorMode


def test_warning_str_returns_message() -> None:
    warning = Warning(
        code='unstructured',
        message='algum aviso de teste',
        orgao=None,
        competencia=None,
        inms_key=None,
        categoria=None,
    )
    assert str(warning) == 'algum aviso de teste'


def test_unmatched_in_values_warnings_fully_unmatched() -> None:
    """Nenhum valor de `in_values` bate com o CSV — mensagem de
    typo/renomeação, categoria fica sem linhas."""
    entries = [
        (
            'ATENDIMENTO_N1',
            GrupoExecutorMode(mode='grupo_executor', in_values=['N1', 'N0']),
        ),
    ]
    raw_csv_path = Path('/tmp/inms-01.csv')

    warnings = unmatched_in_values_warnings(
        inms_key='1.1',
        orgao='MinC',
        competencia='2026-06',
        entries=entries,
        real_values={'Outro Grupo'},
        raw_csv_path=raw_csv_path,
    )

    assert len(warnings) == 1
    warning = warnings[0]
    assert isinstance(warning, Warning)
    assert warning.code == 'in_values_unmatched'
    assert warning.orgao == 'MinC'
    assert warning.competencia == '2026-06'
    assert warning.inms_key == '1.1'
    assert warning.categoria == 'ATENDIMENTO_N1'
    assert 'possível typo/renomeação, categoria ficará sem linhas' in str(
        warning
    )


def test_unmatched_in_values_warnings_partial_match() -> None:
    """Parte de `in_values` bate com o CSV — mensagem "valores não
    encontrados", categoria mantém as linhas que casaram."""
    entries = [
        (
            'ATENDIMENTO_N1',
            GrupoExecutorMode(mode='grupo_executor', in_values=['N1', 'N0']),
        ),
    ]
    raw_csv_path = Path('/tmp/inms-01.csv')

    warnings = unmatched_in_values_warnings(
        inms_key='1.1',
        orgao='MinC',
        competencia='2026-06',
        entries=entries,
        real_values={'N1'},
        raw_csv_path=raw_csv_path,
    )

    assert len(warnings) == 1
    warning = warnings[0]
    assert isinstance(warning, Warning)
    assert warning.code == 'in_values_unmatched'
    assert warning.orgao == 'MinC'
    assert warning.competencia == '2026-06'
    assert warning.inms_key == '1.1'
    assert warning.categoria == 'ATENDIMENTO_N1'
    assert 'valores não encontrados no CSV' in str(warning)


def test_unmatched_in_values_warnings_no_entries_with_in_values() -> None:
    """`catch_all_contains` (sem `in_values`) nunca gera este tipo de aviso."""
    entries = [
        (
            'OPERACAO_N3',
            GrupoExecutorMode(
                mode='grupo_executor', catch_all_contains='(CIT)'
            ),
        ),
    ]

    warnings = unmatched_in_values_warnings(
        inms_key='1.1',
        orgao='MinC',
        competencia='2026-06',
        entries=entries,
        real_values={'(CIT) - Infra'},
        raw_csv_path=Path('/tmp/inms-01.csv'),
    )

    assert warnings == []


def test_outros_warning() -> None:
    warning = outros_warning(
        inms_key='1.1',
        orgao='MTur',
        competencia='2026-07',
        outros_count=3,
    )

    assert isinstance(warning, Warning)
    assert warning.code == 'outros_leftover'
    assert warning.orgao == 'MTur'
    assert warning.competencia == '2026-07'
    assert warning.inms_key == '1.1'
    assert warning.categoria == 'outros'
    assert str(warning) == (
        'INMS 1.1 (MTur/2026-07), categoria outros: 3 linha(s) não '
        'classificada(s) em nenhuma categoria — revisar categorias.yaml'
    )
