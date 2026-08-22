"""Especificação do formulário interativo (ticket 05 SRP) — os 7 campos
coletados pelo fluxo guiado, fora de `interactive/flow.py`.

Extraído de `flow.py`: o *spec* dos campos (prompt/default/ajuda/validador) é
dado declarativo; a UI (como perguntar, confirmar, reentrar) continua no flow.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pyauditor.periodo import month_bounds

__all__: Final[tuple[str, ...]] = (
    "Field",
    "fields_spec",
    "validate_competencia",
    "validate_non_empty_text",
)

_HELP_TOKEN: Final[str] = "?"


def validate_competencia(text: str) -> bool | str:
    """Validate a reporting period using the domain period parser.

    The help token is accepted so the calling prompt can display contextual
    guidance instead of treating it as invalid input.
    """
    if text == _HELP_TOKEN:
        return True

    try:
        month_bounds(text)
    except (TypeError, ValueError):
        return "Competência inválida. Use AAAA-MM com um mês entre 01 e 12, por exemplo 2026-06."

    return True


def validate_non_empty_text(text: str) -> bool | str:
    """Require non-empty text while allowing the contextual-help token."""
    if text == _HELP_TOKEN:
        return True

    if not text.strip():
        return "Informe um valor ou digite '?' para obter ajuda."

    return True


@dataclass(frozen=True, slots=True)
class Field:
    """One guided-form field's declarative contract."""

    key: str
    prompt: str
    default: str
    help_text: str
    validate: Callable[[str], bool | str] | None = None
    is_path: bool = False


fields_spec: Final[tuple[Field, ...]] = (
    Field(
        key="competencia",
        prompt="Competência (AAAA-MM):",
        default="",
        help_text=(
            "A competência é o mês de aferição. Use AAAA-MM, por exemplo "
            "2026-06 para junho de 2026."
        ),
        validate=validate_competencia,
    ),
    Field(
        key="orgao",
        prompt="Órgão:",
        default="MinC",
        help_text=(
            "Escolha MinC ou MTur para processar somente um órgão. "
            "Escolha both para executar o plano phase-major dos dois órgãos "
            "e, quando selecionada, a consolidação final."
        ),
    ),
    Field(
        key="config_dir",
        prompt="Diretório de configurações:",
        default="configs",
        help_text=(
            "Diretório raiz que contém _shared ou os diretórios de "
            "configuração específicos de cada órgão."
        ),
        validate=validate_non_empty_text,
        is_path=True,
    ),
    Field(
        key="data_dir",
        prompt="Diretório de dados:",
        default="input",
        help_text=(
            "Diretório raiz dos dados de entrada, incluindo os "
            "subdiretórios dos órgãos e os arquivos compartilhados."
        ),
        validate=validate_non_empty_text,
        is_path=True,
    ),
    Field(
        key="output_dir",
        prompt="Diretório de ROMs:",
        default="roms",
        help_text=(
            "Diretório onde measure grava os resumos e demais artefatos "
            "ROM utilizados por report e consolidate."
        ),
        validate=validate_non_empty_text,
        is_path=True,
    ),
    Field(
        key="report_dir",
        prompt="Diretório de relatórios:",
        default="reports",
        help_text=(
            "Diretório de destino dos relatórios individuais, arquivos "
            "sintéticos e relatório consolidado."
        ),
        validate=validate_non_empty_text,
        is_path=True,
    ),
    Field(
        key="capa_path",
        prompt="Caminho-base da capa:",
        default="input/capa.csv",
        help_text=(
            "Caminho-base usado para localizar ou criar a capa de cada "
            "órgão. A resolução final é feita pelo helper canônico de "
            "caminhos de capa."
        ),
        validate=validate_non_empty_text,
        is_path=True,
    ),
)