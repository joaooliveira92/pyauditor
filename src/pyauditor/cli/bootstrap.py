"""`pyauditor bootstrap` — create the Excel capa if it doesn't exist yet."""

from dataclasses import dataclass
from pathlib import Path

from pyauditor.cli.results import DependencyCheck, Status
from pyauditor.excel.capa import bootstrap_capa
from pyauditor.logging import logger


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    status: Status
    orgao: str
    capa_path: Path
    created: bool  # False = capa já existia
    warnings: tuple[str, ...]
    error_message: str | None


def check_bootstrap_ready(*_args: object, **_kwargs: object) -> DependencyCheck:
    """`bootstrap` is the first Command in the chain — no dependencies."""
    return DependencyCheck(satisfied=True, missing=())


def run_bootstrap(capa_path: Path, orgao: str) -> BootstrapResult:
    try:
        created = bootstrap_capa(capa_path)
    except OSError as exc:
        message = f"falha ao criar capa em {capa_path}: {exc}"
        logger.error(message)
        return BootstrapResult(
            status="error", orgao=orgao, capa_path=capa_path, created=False,
            warnings=(), error_message=message,
        )
    except Exception as exc:  # boundary: never leak a raw traceback past the CLI
        message = f"falha inesperada ao criar capa em {capa_path}: {exc}"
        logger.error(message)
        return BootstrapResult(
            status="error", orgao=orgao, capa_path=capa_path, created=False,
            warnings=(), error_message=message,
        )

    if created:
        logger.info(f"capa criada: {capa_path}")
    else:
        logger.info(f"capa já existe, nada a fazer: {capa_path}")
    return BootstrapResult(
        status="done", orgao=orgao, capa_path=capa_path, created=created,
        warnings=(), error_message=None,
    )
