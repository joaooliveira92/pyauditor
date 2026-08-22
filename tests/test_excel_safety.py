"""`excel/_safety.py` — sanitização contra formula injection, reusável por
qualquer renderer que grave texto vindo de CSV/YAML externo.
"""

import pytest

from pyauditor.excel._safety import safe_excel_text


@pytest.mark.parametrize(
    'raw',
    [
        '=HYPERLINK("https://exemplo.invalid","Clique aqui")',
        '+1+1',
        '-1+1',
        '@SUM(A1)',
    ],
)
def test_prefixes_dangerous_leading_characters(raw: str) -> None:
    assert safe_excel_text(raw) == f"'{raw}"


@pytest.mark.parametrize('raw', ['Fulano de Tal', 'N1', '', '(CIT) - Infra'])
def test_leaves_ordinary_text_untouched(raw: str) -> None:
    assert safe_excel_text(raw) == raw
