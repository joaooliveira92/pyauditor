"""Utilitário de parsing YAML de alta performance.

Usa `CSafeLoader` (implementação acelerada em C do PyYAML) quando
disponível, reduzindo o tempo de parsing em até ~9x em comparação com
`yaml.safe_load` puro em Python.
"""

from __future__ import annotations

from typing import IO, Final

import yaml

__all__: Final[tuple[str, ...]] = ('safe_load_yaml',)

# CSafeLoader aproveita libyaml em C quando compilado com suporte a C,
# reduzindo significativamente o tempo de carga de YAMLs no pipeline e
# nos testes.
try:
    from yaml import CSafeLoader as _SafeLoader
except ImportError:  # pragma: no cover
    from yaml import SafeLoader as _SafeLoader  # type: ignore[assignment]


def safe_load_yaml(stream: str | bytes | IO[str] | IO[bytes]) -> object:
    """Carrega dados YAML de forma segura utilizando o carregador mais
    rápido disponível."""
    return yaml.load(stream, Loader=_SafeLoader)
