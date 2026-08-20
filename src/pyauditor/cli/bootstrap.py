"""`pyauditor bootstrap` — create the capa CSVs if they don't exist yet.

Cria o CSV comum (`capa.csv`, campos do contrato) e o CSV do órgão
(`capa_{orgao}.csv`, campos por órgão) ao lado do capa_path — migração das
capas .xlsx para CSV (ticket 07 Q2). `capa.csv` é compartilhado pelos dois
órgãos; o `bootstrap` por órgão cria o comum se faltar e o do órgão pedido.
"""

from dataclasses import dataclass
from pathlib import Path

from pyauditor.cli.results import WRITE_FAILURE_HINT, DependencyCheck, Status
from pyauditor.excel.capa import (
    COMMON_FIELD_LABELS,
    ORGAO_FIELD_LABELS,
    bootstrap_capa_csv,
)
from pyauditor.logging import log_event, logger

CAPA_COMUM_NAME = "capa.csv"


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    status: Status
    orgao: str
    capa_path: Path  # CSV do órgão (o destino por-órgão)
    created: bool  # True se algum arquivo (comum ou do órgão) foi criado
    warnings: tuple[str, ...]
    error_message: str | None


def check_bootstrap_ready(*_args: object, **_kwargs: object) -> DependencyCheck:
    """`bootstrap` is the first Command in the chain — no dependencies."""
    return DependencyCheck(satisfied=True, missing=())


def run_bootstrap(capa_path: Path, orgao: str) -> BootstrapResult:
    """Creates the common `capa.csv` and the per-órgão `capa_{orgao}.csv`
    next to `capa_path` (which is the per-órgão path; its parent holds the
    whole capa family). Idempotent — an existing file is never touched."""
    data_dir = capa_path.parent
    comum_path = data_dir / CAPA_COMUM_NAME
    orgao_path = capa_path

    created = False
    try:
        created_common = bootstrap_capa_csv(comum_path, COMMON_FIELD_LABELS)
        created |= created_common
        created_orgao = bootstrap_capa_csv(orgao_path, ORGAO_FIELD_LABELS)
        created |= created_orgao
    except OSError as exc:
        message = f"falha ao criar capa em {data_dir}: {exc} — {WRITE_FAILURE_HINT}"
        logger.error(message)
        return BootstrapResult(
            status="error", orgao=orgao, capa_path=orgao_path, created=False,
            warnings=(), error_message=message,
        )
    except Exception as exc:  # boundary: never leak a raw traceback past the CLI
        message = f"falha inesperada ao criar capa em {data_dir}: {exc}"
        logger.error(message)
        return BootstrapResult(
            status="error", orgao=orgao, capa_path=orgao_path, created=False,
            warnings=(), error_message=message,
        )

    if created_orgao:
        log_event("capa_created", "capa criada", "INFO", orgao=orgao, arquivo=str(orgao_path))
    else:
        # Revisão §3: "nada a fazer" era impreciso — o arquivo é reutilizado.
        log_event(
            "capa_reused", "capa existente será reutilizada", "INFO",
            orgao=orgao, arquivo=str(orgao_path),
        )
    return BootstrapResult(
        status="done", orgao=orgao, capa_path=orgao_path, created=created,
        warnings=(), error_message=None,
    )