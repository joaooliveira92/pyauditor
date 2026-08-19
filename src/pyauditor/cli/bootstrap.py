"""`pyauditor bootstrap` — create the Excel capa if it doesn't exist yet."""

from pathlib import Path

from pyauditor.excel.capa import bootstrap_capa
from pyauditor.logging import logger


def run_bootstrap(capa_path: Path) -> int:
    try:
        created = bootstrap_capa(capa_path)
    except OSError as exc:
        logger.error(f"falha ao criar capa em {capa_path}: {exc}")
        return 1

    if created:
        logger.info(f"capa criada: {capa_path}")
    else:
        logger.info(f"capa já existe, nada a fazer: {capa_path}")
    return 0
