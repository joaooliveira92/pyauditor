from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pyauditor.interactive.provider import (
    InteractionCancelledError,
    RichQuestionaryProvider,
)


def _cancelled_ask() -> MagicMock:
    """A `questionary.*` object whose `.ask()` returns `None`, exactly what
    real `questionary` returns on Ctrl+C/EOF."""
    mock = MagicMock()
    mock.ask.return_value = None
    return mock


@pytest.mark.parametrize(
    'questionary_target,call',
    [
        (
            'pyauditor.interactive.provider.questionary.text',
            lambda p: p.ask_text('x'),
        ),
        (
            'pyauditor.interactive.provider.questionary.select',
            lambda p: p.ask_choice('x', ['a']),
        ),
        (
            'pyauditor.interactive.provider.questionary.checkbox',
            lambda p: p.ask_multi_choice('x', [('a', 'a', True, None)]),
        ),
        (
            'pyauditor.interactive.provider.questionary.confirm',
            lambda p: p.confirm('x'),
        ),
    ],
)
def test_ctrl_c_raises_interaction_cancelled_instead_of_a_fake_answer(
    questionary_target: str, call: Any
) -> None:
    provider = RichQuestionaryProvider()
    with (
        patch(questionary_target, return_value=_cancelled_ask()),
        pytest.raises(InteractionCancelledError),
    ):
        call(provider)
