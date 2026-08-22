"""`pyauditor bootstrap` — create the capa CSVs if they don't exist yet.

Cria o CSV comum (`capa.csv`, campos do contrato) e o CSV do órgão
(`capa_{orgao}.csv`, campos por órgão) ao lado do capa_path — migração das
capas .xlsx para CSV (ticket 07). `capa.csv` é compartilhado pelos dois
órgãos; o `bootstrap` por órgão cria o comum se faltar e o do órgão pedido.

Spec competencia-cli-equipe §6/§7: também cria o esqueleto de
`equipe.csv` (fonte única dos responsáveis) na mesma pasta — cabeçalho
`FUNÇÃO,NOME,SIAPE` e uma linha vazia por função titular + uma por
"- Substituto". Idempotente como as capas: existente nunca é tocado.
"""

from dataclasses import dataclass
from pathlib import Path

from pyauditor.atomic_write import atomic_write
from pyauditor.cli.results import WRITE_FAILURE_HINT, DependencyCheck, Status
from pyauditor.excel.capa import (
    COMMON_FIELD_LABELS,
    ORGAO_FIELD_LABELS,
    bootstrap_capa_csv,
)
from pyauditor.excel.equipe import (
    EQUIPE_ENCODING,
    EQUIPE_FILENAME,
    RESPONSAVEL_LABELS,
)
from pyauditor.logging import log_event, logger

CAPA_COMUM_NAME = 'capa.csv'

_SUBSTITUTO_LABEL_SUFFIX = ' - Substituto'


def _equipe_csv_text() -> str:
    """Esqueleto hand-fill do `equipe.csv`: 4 titulares + 4 substitutos."""
    linhas = ['FUNÇÃO,NOME,SIAPE']
    substitutos = (
        f'{label}{_SUBSTITUTO_LABEL_SUFFIX}' for label in RESPONSAVEL_LABELS
    )
    for label in (*RESPONSAVEL_LABELS, *substitutos):
        linhas.append(f'{label},,')
    return '\n'.join(linhas) + '\n'


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
    """Creates the common `capa.csv`, the per-órgão `capa_{orgao}.csv` and
    the `equipe.csv` skeleton next to `capa_path` (which is the per-órgão
    path; its parent holds the whole capa family). Idempotent — an existing
    file is never touched."""
    data_dir = capa_path.parent
    comum_path = data_dir / CAPA_COMUM_NAME
    orgao_path = capa_path

    created = False
    created_equipe = False
    try:
        created_common = bootstrap_capa_csv(comum_path, COMMON_FIELD_LABELS)
        created |= created_common
        created_orgao = bootstrap_capa_csv(orgao_path, ORGAO_FIELD_LABELS)
        created |= created_orgao
        equipe_path = data_dir / EQUIPE_FILENAME
        if not equipe_path.exists():
            atomic_write(
                equipe_path,
                lambda p: p.write_text(
                    _equipe_csv_text(), encoding=EQUIPE_ENCODING
                ),
            )
            created_equipe = True
            created = True
    except OSError as exc:
        message = (
            f'falha ao criar capa em {data_dir}: {exc} — {WRITE_FAILURE_HINT}'
        )
        logger.error(message)
        return BootstrapResult(
            status='error',
            orgao=orgao,
            capa_path=orgao_path,
            created=False,
            warnings=(),
            error_message=message,
        )
    except (
        Exception
    ) as exc:  # boundary: never leak a raw traceback past the CLI
        message = f'falha inesperada ao criar capa em {data_dir}: {exc}'
        logger.error(message)
        return BootstrapResult(
            status='error',
            orgao=orgao,
            capa_path=orgao_path,
            created=False,
            warnings=(),
            error_message=message,
        )

    if created_orgao:
        log_event(
            'capa_created',
            'capa criada',
            'INFO',
            orgao=orgao,
            arquivo=str(orgao_path),
        )
    else:
        # Revisão §3: "nada a fazer" era impreciso — o arquivo é reutilizado.
        log_event(
            'capa_reused',
            'capa existente será reutilizada',
            'INFO',
            orgao=orgao,
            arquivo=str(orgao_path),
        )
    if created_equipe:
        log_event(
            'equipe_created',
            'esqueleto de equipe criado',
            'INFO',
            arquivo=str(equipe_path),
        )
    return BootstrapResult(
        status='done',
        orgao=orgao,
        capa_path=orgao_path,
        created=created,
        warnings=(),
        error_message=None,
    )
