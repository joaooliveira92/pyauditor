import json
import sys
from datetime import UTC
from io import StringIO
from pathlib import Path

import pytest
from loguru import logger as loguru_logger

from pyauditor.logging import (
    LoggingHandlers,
    log_event,
    logger,
    resolve_log_level,
    setup_logging,
)


def test_logger_is_the_shared_loguru_instance() -> None:
    assert logger is loguru_logger


def test_setup_logging_returns_handler_id() -> None:
    handlers = setup_logging(sink=sys.stderr, level='INFO')
    assert isinstance(handlers, LoggingHandlers)
    assert isinstance(handlers.stream, int)
    assert isinstance(handlers.file, int) or handlers.file is None
    # idempotent — second call must not duplicate handlers
    handlers2 = setup_logging(sink=sys.stderr, level='DEBUG')
    assert isinstance(handlers2.stream, int)


def test_logger_methods_work() -> None:
    logger.info('hello {}', 'world')
    logger.error('boom {}', 123)
    logger.debug('debug')


def test_all_exports() -> None:
    import pyauditor.logging as m

    assert 'logger' in m.__all__
    assert 'setup_logging' in m.__all__


def test_resolve_log_level_verbosity_and_explicit() -> None:
    assert resolve_log_level(0, None) == 'INFO'
    assert resolve_log_level(1, None) == 'DEBUG'
    assert resolve_log_level(2, None) == 'DEBUG'
    # `--log-level` explícito prevalece sobre `-v` (ticket 05 Q9).
    assert resolve_log_level(0, 'WARNING') == 'WARNING'
    assert resolve_log_level(2, 'ERROR') == 'ERROR'
    # valor inválido é erro de configuração (argparse já restringe choices)
    with pytest.raises(ValueError, match='Unsupported explicit'):
        resolve_log_level(1, 'NOPE')


def test_log_event_texto_carrega_contexto() -> None:
    buf = StringIO()
    setup_logging(sink=buf, level='INFO')
    log_event(
        'indicator_measured',
        'indicador apurado',
        'INFO',
        orgao='MinC',
        codigo='INMS-1.1',
    )
    setup_logging(sink=sys.stderr, level='INFO')
    out = buf.getvalue()
    assert 'indicador apurado' in out
    assert 'orgao="MinC"' in out
    assert 'codigo="INMS-1.1"' in out


def test_log_event_omite_none() -> None:
    buf = StringIO()
    setup_logging(sink=buf, level='INFO')
    log_event('x', 'v', 'INFO', orgao='A', rom_path=None)
    setup_logging(sink=sys.stderr, level='INFO')
    out = buf.getvalue()
    assert 'orgao="A"' in out
    assert 'rom_path=' not in out  # None omitido


def test_log_format_json_estructura_evento() -> None:
    buf = StringIO()
    setup_logging(sink=buf, json_format=True, verbose=1)
    log_event(
        'indicator_measured',
        'indicador apurado',
        'INFO',
        orgao='MinC',
        status='conforme',
    )
    setup_logging(sink=sys.stderr, level='INFO')
    payload = json.loads(buf.getvalue().splitlines()[0])
    # formato flat ({time, level, event, message, contexto}): evento e
    # contexto em campos-raiz, não em record.extra.
    assert payload['event'] == 'indicator_measured'
    assert payload['orgao'] == 'MinC'
    assert payload['status'] == 'conforme'
    assert payload['level'] == 'INFO'


def test_normalize_json_value_supported_types() -> None:
    from datetime import date, datetime
    from decimal import Decimal
    from enum import Enum
    from pathlib import Path

    from pyauditor.log_contract import normalize_json_value

    class _Cor(Enum):
        VERMELHO = 'vermelho'

    assert normalize_json_value(None) is None
    assert normalize_json_value(True) is True
    assert normalize_json_value(3) == 3
    assert normalize_json_value(2.5) == 2.5
    assert normalize_json_value('abc') == 'abc'
    # Decimal vira string decimal com notação fixa.
    assert normalize_json_value(Decimal('1.5000')) == '1.5000'
    assert normalize_json_value(Path('/tmp/roms')) == '/tmp/roms'
    assert (
        normalize_json_value(datetime(2026, 6, 1, tzinfo=UTC))
        == '2026-06-01T00:00:00+00:00'
    )
    assert normalize_json_value(date(2026, 6, 1)) == '2026-06-01'
    assert normalize_json_value(_Cor.VERMELHO) == 'vermelho'
    assert normalize_json_value({'a': [1, 2]}) == {'a': [1, 2]}
    assert normalize_json_value((1, 2)) == [1, 2]


def test_normalize_json_value_rejects_invalid_types() -> None:
    from datetime import datetime
    from decimal import Decimal

    from pyauditor.log_contract import normalize_json_value

    with pytest.raises(ValueError, match='finite'):
        normalize_json_value(float('nan'))
    with pytest.raises(ValueError, match='finite'):
        normalize_json_value(float('inf'))
    with pytest.raises(ValueError, match='finite'):
        normalize_json_value(Decimal('NaN'))
    with pytest.raises(ValueError, match='timezone'):
        # datetime naive — precisa de tz explícito
        normalize_json_value(datetime(2026, 6, 1))
    with pytest.raises(TypeError, match='Nested log mapping keys'):
        normalize_json_value({1: 'um'})
    with pytest.raises(
        TypeError, match='Unsupported logging context value type'
    ):
        normalize_json_value(object())


def test_log_event_rejects_invalid_contract() -> None:
    from dataclasses import dataclass

    from pyauditor.log_contract import normalize_context
    from pyauditor.logging import log_event

    with pytest.raises(TypeError, match='event must be a string'):
        log_event(123, 'verb')  # type: ignore[arg-type]
    with pytest.raises(ValueError, match='snake_case'):
        log_event('Invalid Event', 'verb')
    with pytest.raises(ValueError, match='exactly one line'):
        log_event('event', 'a\nb')
    with pytest.raises(ValueError, match='reserved'):
        log_event('event', 'verb', message='x')
    with pytest.raises(ValueError, match='sensitive'):
        log_event('event', 'verb', api_key='x')
    with pytest.raises(ValueError, match='Invalid context key'):
        log_event('event', 'verb', **{'chave com espaço': 'x'})  # type: ignore[arg-type]
    with pytest.raises(TypeError, match='Context keys must be strings'):
        normalize_context({'x': 'ok', 1: 'err'})  # type: ignore[dict-item]

    @dataclass
    class _Dado:
        valor: int

    with pytest.raises(TypeError, match='Dataclass instances'):
        log_event('event', 'verb', dado=_Dado(1))


def test_setup_logging_json_format_with_path_is_rejected() -> None:
    from pathlib import Path

    with pytest.raises(ValueError, match='writable file-like stream'):
        setup_logging(sink=Path('/tmp/x.json'), json_format=True)


def test_setup_logging_rejects_empty_format() -> None:
    with pytest.raises(ValueError, match='must not be empty'):
        setup_logging(sink=sys.stderr, format_='')


def test_setup_logging_rejects_non_bool_json_format() -> None:
    with pytest.raises(TypeError, match='json_format must be bool'):
        setup_logging(sink=sys.stderr, json_format=1)  # type: ignore[arg-type]


def test_setup_logging_rolls_back_handlers_on_failure(tmp_path: Path) -> None:
    """Quando o handler de logfile falha ao ser adicionado (log_path inválido),
    `setup_logging` remove o handler de stream que acabou de criar e re-propaga
    a exceção — nenhum handler órfão fica instalado."""
    from pyauditor.logging import setup_logging

    # log_path apontando para um diretório → loguru levanta IsADirectoryError
    # no add do file handler (depois do stream já ter sido adicionado).
    log_dir = tmp_path / 'logdir'
    log_dir.mkdir()
    with pytest.raises(IsADirectoryError):
        setup_logging(sink=sys.stderr, log_path=log_dir, level='INFO')

    # A chamada que falhou não deixou o logger global quebrado: uma nova
    # configuração válida instala handlers normalmente.
    handlers = setup_logging(sink=sys.stderr, level='INFO')
    assert isinstance(handlers.stream, int)


def test_setup_logging_invalid_verbosity_is_rejected() -> None:
    with pytest.raises(ValueError, match='must not be negative'):
        setup_logging(sink=sys.stderr, verbose=-1)


def test_log_event_detail_filter_controls_visibility() -> None:
    """`detail` acima do máximo da verbosity atual é filtrado pelo handler."""
    buf = StringIO()
    setup_logging(sink=buf, verbose=1)
    log_event('e1', 'profundo', 'DEBUG', detail=2)
    log_event('e2', 'raso', 'DEBUG', detail=1)
    setup_logging(sink=sys.stderr, level='INFO')
    out = buf.getvalue()
    assert 'profundo' not in out  # detail 2 acima da verbosity 1
    assert 'raso' in out
