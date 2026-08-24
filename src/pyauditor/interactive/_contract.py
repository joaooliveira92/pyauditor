"""Contrato de interação do fluxo guiado (ticket 10 SRP).

`InteractionProvider` (Protocol), `InteractionCancelledError`,
`MultiChoiceOption` e `TextValidator` vivem aqui, sem acoplamento a Rich ou
Questionary. A implementação de produção (`RichQuestionaryProvider`) mora em
`rich_provider.py`; `interactive/provider.py` reexporta ambos preservando a
API pública.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Final, Protocol, runtime_checkable

from pyauditor.orchestration.run import RunResult

__all__: Final[tuple[str, ...]] = (
    'InteractionCancelledError',
    'InteractionProvider',
    'MultiChoiceOption',
    'TextValidator',
)

type TextValidator = Callable[[str], bool | str]
type MultiChoiceOption = tuple[str, str, bool, str | None]


class InteractionCancelledError(Exception):
    """Signal that the user cancelled an interactive operation.

    Providers raise this exception when their underlying prompt library
    reports cancellation, including Ctrl+C or end-of-input when represented
    as a cancelled answer.

    The guided-flow entry point catches this exception once and translates it
    into the cancellation exit code. Other prompt and terminal failures are
    not converted to cancellation and propagate to the caller.
    """


@runtime_checkable
class InteractionProvider(Protocol):
    """Define all prompting and output operations used by the guided flow.

    Implementations may use a terminal, test fixture, graphical interface, or
    another interaction mechanism. They must preserve literal text and convert
    explicit user cancellation into :class:`InteractionCancelledError`.
    """

    def ask_text(
        self,
        message: str,
        *,
        default: str = '',
        validate: TextValidator | None = None,
    ) -> str:
        """Prompt for text.

        Args:
            message: Literal prompt shown to the user.
            default: Initial value offered by the prompt.
            validate: Optional validator receiving the current input. It
                returns ``True`` for valid input or an explanatory string for
                invalid input.

        Returns:
            The text entered or accepted by the user.

        Raises:
            InteractionCancelledError: If the prompt is cancelled.
        """
        ...

    def ask_choice(
        self,
        message: str,
        choices: Sequence[str],
        *,
        default: str | None = None,
    ) -> str:
        """Prompt for one value from a sequence of choices.

        Args:
            message: Literal prompt shown to the user.
            choices: Values available for selection.
            default: Initially selected value, when applicable.

        Returns:
            The selected value.

        Raises:
            InteractionCancelledError: If the prompt is cancelled.
            ValueError: If ``choices`` is empty or ``default`` is not one of
                the available choices.
        """
        ...

    def ask_multi_choice(
        self,
        message: str,
        choices: Sequence[MultiChoiceOption],
    ) -> list[str]:
        """Prompt for zero or more values.

        Each option is represented by:

        ``(label, value, checked, disabled_reason)``

        ``label``
            Literal text displayed to the user.

        ``value``
            Value returned when the option is selected.

        ``checked``
            Whether the option is selected initially.

        ``disabled_reason``
            When non-``None``, disables the option and explains why it cannot
            be selected.

        Args:
            message: Literal prompt shown to the user.
            choices: Available multiple-choice options.

        Returns:
            Selected option values in provider order.

        Raises:
            InteractionCancelledError: If the prompt is cancelled.
            ValueError: If no options are supplied or option values are
                duplicated.
        """
        ...

    def confirm(
        self,
        message: str,
        *,
        default: bool = True,
    ) -> bool:
        """Prompt for a boolean confirmation.

        Raises:
            InteractionCancelledError: If the prompt is cancelled.
        """
        ...

    def show_message(
        self,
        text: str,
        *,
        style: str = '',
    ) -> None:
        """Display literal text with an optional presentation style.

        ``text`` must not be interpreted as Rich or another markup language.
        The style applies to the complete message.
        """
        ...

    def show_progress(
        self,
        label: str,
    ) -> AbstractContextManager[None]:
        """Display a progress indicator for the context lifetime.

        The label is rendered literally. The progress indicator must be
        stopped when the context exits, including exceptional exits.
        """
        ...

    def show_summary(
        self,
        run_result: RunResult,
        *,
        log_path: Path | str | None = None,
    ) -> int:
        """Render the canonical completion summary and return its exit code."""
        ...
