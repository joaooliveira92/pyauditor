"""Define the injectable interaction boundary for guided CLI workflows.

The guided flow communicates exclusively through
:class:`InteractionProvider`. This keeps prompting, terminal rendering, and
progress display separate from orchestration and business logic.

Every provider implementation must support the complete interaction surface:

- validated free-text input;
- single-choice and multiple-choice prompts;
- confirmation prompts;
- literal styled messages;
- progress indicators;
- final run-summary rendering.

Prompt cancellation must raise :class:`InteractionCancelled`. Providers must
never convert cancellation into an empty string, an empty selection, or a
negative confirmation because those values are valid user answers with
different meanings.

Dynamic text is treated as literal content. Provider implementations must not
interpret paths, organization names, validation messages, or error messages as
terminal markup.

:class:`RichQuestionaryProvider` is the production implementation. It uses
Questionary for prompts and Rich for output while preserving the provider
contract required by the guided flow and its test doubles.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from typing import Final, Protocol, runtime_checkable

import questionary
from rich.console import Console
from rich.text import Text

from pyauditor.orchestration.run import RunResult
from pyauditor.orchestration.summary import (
    exit_code_for_run,
    render_summary,
)

__all__: Final[tuple[str, ...]] = (
    "InteractionCancelled",
    "InteractionProvider",
    "MultiChoiceOption",
    "RichQuestionaryProvider",
    "TextValidator",
)

type TextValidator = Callable[[str], bool | str]
type MultiChoiceOption = tuple[str, str, bool, str | None]


class InteractionCancelled(Exception):
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
    explicit user cancellation into :class:`InteractionCancelled`.
    """

    def ask_text(
        self,
        message: str,
        *,
        default: str = "",
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
            InteractionCancelled: If the prompt is cancelled.
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
            InteractionCancelled: If the prompt is cancelled.
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
            InteractionCancelled: If the prompt is cancelled.
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
            InteractionCancelled: If the prompt is cancelled.
        """
        ...

    def show_message(
        self,
        text: str,
        *,
        style: str = "",
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


class RichQuestionaryProvider:
    """Provide production terminal interaction with Questionary and Rich.

    Questionary handles prompting while Rich handles messages, progress, and
    completion-summary output. Answers reported as ``None`` by Questionary are
    treated as cancellation.

    Dynamic content is wrapped in :class:`rich.text.Text`, ensuring that paths,
    errors, and other user-controlled values are rendered literally rather
    than interpreted as Rich markup.
    """

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the provider.

        Args:
            console: Optional Rich console. Supplying one allows output
                capture, stream selection, color configuration, and testing.
        """
        self._console = console if console is not None else Console()

    def ask_text(
        self,
        message: str,
        *,
        default: str = "",
        validate: TextValidator | None = None,
    ) -> str:
        """Prompt for validated text."""
        answer = questionary.text(
            message,
            default=default,
            validate=validate,
        ).ask()

        if answer is None:
            raise InteractionCancelled

        if not isinstance(answer, str):
            raise TypeError(
                f"Questionary text prompt returned a non-string answer: {type(answer).__name__}."
            )

        return answer

    def ask_choice(
        self,
        message: str,
        choices: Sequence[str],
        *,
        default: str | None = None,
    ) -> str:
        """Prompt for one value from a non-empty sequence."""
        normalized_choices = tuple(choices)

        if not normalized_choices:
            raise ValueError("Single-choice prompt requires at least one option.")

        if any(not isinstance(choice, str) for choice in normalized_choices):
            raise TypeError("Single-choice prompt options must all be strings.")

        if default is not None and default not in normalized_choices:
            raise ValueError(f"Default choice {default!r} is not available.")

        answer = questionary.select(
            message,
            choices=list(normalized_choices),
            default=default,
        ).ask()

        if answer is None:
            raise InteractionCancelled

        if not isinstance(answer, str):
            raise TypeError(
                f"Questionary select prompt returned a non-string answer: {type(answer).__name__}."
            )

        if answer not in normalized_choices:
            raise ValueError(f"Questionary returned an unavailable choice: {answer!r}.")

        return answer

    def ask_multi_choice(
        self,
        message: str,
        choices: Sequence[MultiChoiceOption],
    ) -> list[str]:
        """Prompt for multiple values using validated option definitions."""
        normalized_choices = tuple(choices)

        if not normalized_choices:
            raise ValueError("Multiple-choice prompt requires at least one option.")

        values: list[str] = []
        options: list[questionary.Choice] = []

        for index, option in enumerate(normalized_choices):
            if len(option) != 4:
                raise ValueError(
                    f"Multiple-choice option {index} must contain exactly four fields."
                )

            label, value, checked, disabled_reason = option

            if not label:
                raise ValueError(f"Multiple-choice option {index} has an empty label.")

            if not value:
                raise ValueError(f"Multiple-choice option {index} has an empty value.")

            if not isinstance(checked, bool):
                raise TypeError(f"Multiple-choice option {index} checked state must be boolean.")

            if disabled_reason is not None and not disabled_reason.strip():
                raise ValueError(f"Multiple-choice option {index} has an empty disabled reason.")

            values.append(value)
            options.append(
                questionary.Choice(
                    title=label,
                    value=value,
                    checked=checked,
                    disabled=disabled_reason,
                )
            )

        if len(values) != len(set(values)):
            raise ValueError("Multiple-choice option values must be unique.")

        answer = questionary.checkbox(
            message,
            choices=options,
        ).ask()

        if answer is None:
            raise InteractionCancelled

        if not isinstance(answer, list):
            raise TypeError(
                "Questionary checkbox returned an invalid answer container: "
                f"{type(answer).__name__}."
            )

        if any(not isinstance(value, str) for value in answer):
            raise TypeError("Questionary checkbox returned a non-string option value.")

        unknown_values = set(answer) - set(values)
        if unknown_values:
            raise ValueError(
                f"Questionary checkbox returned unavailable values: {sorted(unknown_values)!r}."
            )

        return answer

    def confirm(
        self,
        message: str,
        *,
        default: bool = True,
    ) -> bool:
        """Prompt for confirmation without coercing cancellation."""
        answer = questionary.confirm(
            message,
            default=default,
        ).ask()

        if answer is None:
            raise InteractionCancelled

        if not isinstance(answer, bool):
            raise TypeError(
                f"Questionary confirmation returned a non-boolean answer: {type(answer).__name__}."
            )

        return answer

    def show_message(
        self,
        text: str,
        *,
        style: str = "",
    ) -> None:
        """Display literal styled text."""
        self._console.print(
            Text(
                text,
                style=style,
            )
        )

    @contextmanager
    def show_progress(
        self,
        label: str,
    ) -> Iterator[None]:
        """Display and deterministically stop a literal progress indicator."""
        with self._console.status(
            Text(label),
            spinner="dots",
        ):
            yield

    def show_summary(
        self,
        run_result: RunResult,
        *,
        log_path: Path | str | None = None,
    ) -> int:
        """Render the shared text summary and return its aggregate exit code."""
        exit_code = exit_code_for_run(
            run_result.state.commands,
            run_result.results,
        )

        render_summary(
            run_result,
            log_path=log_path,
            output="text",
            console=self._console,
        )

        return exit_code
