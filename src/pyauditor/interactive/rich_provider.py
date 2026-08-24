"""Implementação de produção do `InteractionProvider` (ticket 10 SRP).

Questionary cuida dos prompts; Rich cuida de mensagens, progresso e resumo.
As respostas ``None`` do Questionary são tratadas como cancelamento
(``InteractionCancelledError``). O contrato vive em `interactive/_contract.py`;
este módulo é a implementação concreta, isolada do contrato.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Final

import questionary
from rich.console import Console
from rich.text import Text

from pyauditor.interactive._contract import (
    InteractionCancelledError,
    MultiChoiceOption,
    TextValidator,
)
from pyauditor.orchestration.run import RunResult
from pyauditor.orchestration.summary import (
    exit_code_for_run,
    render_summary,
)

__all__: Final[tuple[str, ...]] = ('RichQuestionaryProvider',)


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
        default: str = '',
        validate: TextValidator | None = None,
    ) -> str:
        """Prompt for validated text."""
        answer = questionary.text(
            message,
            default=default,
            validate=validate,
        ).ask()

        if answer is None:
            raise InteractionCancelledError

        if not isinstance(answer, str):
            raise TypeError(
                f'Questionary text prompt returned a non-string answer:'
                f'{type(answer).__name__}.'
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
            raise ValueError(
                'Single-choice prompt requires at least one option.'
            )

        if any(not isinstance(choice, str) for choice in normalized_choices):
            raise TypeError('Single-choice prompt options must all be strings.')

        if default is not None and default not in normalized_choices:
            raise ValueError(f'Default choice {default!r} is not available.')

        answer = questionary.select(
            message,
            choices=list(normalized_choices),
            default=default,
        ).ask()

        if answer is None:
            raise InteractionCancelledError

        if not isinstance(answer, str):
            raise TypeError(
                f'Questionary select prompt returned a non-string answer:'
                f'{type(answer).__name__}.'
            )

        if answer not in normalized_choices:
            raise ValueError(
                f'Questionary returned an unavailable choice: {answer!r}.'
            )

        return answer

    def ask_multi_choice(
        self,
        message: str,
        choices: Sequence[MultiChoiceOption],
    ) -> list[str]:
        """Prompt for multiple values using validated option definitions."""
        normalized_choices = tuple(choices)

        if not normalized_choices:
            raise ValueError(
                'Multiple-choice prompt requires at least one option.'
            )

        values: list[str] = []
        options: list[questionary.Choice] = []

        for index, option in enumerate(normalized_choices):
            if len(option) != 4:
                raise ValueError(
                    f'Multiple-choice option {index} must contain exactly four '
                    f'fields.'
                )

            label, value, checked, disabled_reason = option

            if not label:
                raise ValueError(
                    f'Multiple-choice option {index} has an empty label.'
                )

            if not value:
                raise ValueError(
                    f'Multiple-choice option {index} has an empty value.'
                )

            if not isinstance(checked, bool):
                raise TypeError(
                    f'Multiple-choice option {index} checked state must be '
                    f'boolean.'
                )

            if disabled_reason is not None and not disabled_reason.strip():
                raise ValueError(
                    f'Multiple-choice option {index} has an empty disabled '
                    f'reason.'
                )

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
            raise ValueError('Multiple-choice option values must be unique.')

        answer = questionary.checkbox(
            message,
            choices=options,
        ).ask()

        if answer is None:
            raise InteractionCancelledError

        if not isinstance(answer, list):
            raise TypeError(
                'Questionary checkbox returned an invalid answer container: '
                f'{type(answer).__name__}.'
            )

        if any(not isinstance(value, str) for value in answer):
            raise TypeError(
                'Questionary checkbox returned a non-string option value.'
            )

        unknown_values = set(answer) - set(values)
        if unknown_values:
            raise ValueError(
                f'Questionary checkbox returned unavailable values:'
                f'{sorted(unknown_values)!r}.'
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
            raise InteractionCancelledError

        if not isinstance(answer, bool):
            raise TypeError(
                f'Questionary confirmation returned a non-boolean answer:'
                f'{type(answer).__name__}.'
            )

        return answer

    def show_message(
        self,
        text: str,
        *,
        style: str = '',
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
            spinner='dots',
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
            output='text',
            console=self._console,
        )

        return exit_code
