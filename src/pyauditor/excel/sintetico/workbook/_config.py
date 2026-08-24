from __future__ import annotations

from pathlib import Path

from pyauditor.categoria_filter import base_config_stem
from pyauditor.config.models import IndicatorConfig
from pyauditor.engine.pipeline import inject_orgao, load_config


def load_base_config(
    inms_key: str, config_dir: Path, orgao: str
) -> IndicatorConfig:
    """Carrega e corrige (`inject_orgao`) a config base de um INMS.

    Raises:
        OSError | ValueError: config ausente/inválida — o chamador degrada
            só a aba deste INMS, nunca o workbook inteiro.
    """
    base_stem = base_config_stem(inms_key)
    return inject_orgao(load_config(config_dir / f'{base_stem}.yaml'), orgao)
