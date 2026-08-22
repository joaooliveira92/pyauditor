"""Logging e observabilidade do pipeline (ticket 05, .scratch/ajuste-cli).

Política de verbosidade (decisões Q1-Q9 do ticket 05):
- padrão (INFO): etapas, pendências e resumo — sem linha por indicador;
- `-v` (DEBUG): um evento por indicador (`indicador apurado ...`);
- `-vv`: detalhes de leitura/validação/cálculo (DEBUG estendido);
- `--log-format json`: cada registro no stream vira um JSON de uma linha
  ({time, level, event, ...message}) — para automação; o arquivo de log
  permanece texto legível (o JSON serve para o stderr consumido por CI).

`--output json` (ticket 04) é uma superfície separada: os logs aqui (stderr/
arquivo) são independentes do resumo final em stdout.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Final, TextIO

from loguru import logger

__all__ = ("log_event", "logger", "resolve_log_level", "setup_logging")

_LOG_FORMAT: Final[str] = "{time:HH:mm:ss} | {level: <8} | {message}"
_FILE_LOG_FORMAT: Final[str] = (
    "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} | {message}"
)
_LOG_LEVEL: Final[str] = "INFO"
_LEVELS: Final[tuple[str, ...]] = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

_VERBOSITY_LEVEL: Final[dict[int, str]] = {0: "INFO", 1: "DEBUG", 2: "DEBUG"}

# Quantos logs de uma mesma execução (bootstrap/measure/run/split) o loguru
# mantém por diretório antes de apagar os mais antigos — evita o acúmulo
# indefinido de `pyauditor-<comando>-<timestamp>.log`.
_LOG_RETENTION: Final[int] = 5


def resolve_log_level(verbosity: int, explicit: str | None) -> str:
    """Nível efetivo de log. `explicit` (--log-level) prevalece sobre a
    verbosidade `-v`/`-vv` (que sobe até DEBUG); senão, INFO."""
    if explicit:
        candidate = explicit.upper()
        return candidate if candidate in _LEVELS else _LOG_LEVEL
    return _VERBOSITY_LEVEL.get(min(verbosity, 2), _LOG_LEVEL)


def log_event(
    event: str,
    verb: str,
    level: str = "INFO",
    **context: object,
) -> None:
    """Registra um evento estruturado: frase legível + contexto chave=valor, e
    o nome `event` reservado para o JSON (`--log-format json`). Valores `None`
    são omitidos — campos ausentes nunca aparecem como vazio/zero.

    Ex.: log_event("indicator_measured", "indicador apurado", "INFO",
    orgao="MinC", codigo="INMS-1.1", rom_path="roms/...", status="conforme")
    texto -> `indicador apurado | orgao=MinC codigo=INMS-1.1 rom_path=... status=conforme`
    JSON  -> {"time":..., "event":"indicator_measured", "orgao":"MinC", ...}
    """
    context = {k: v for k, v in context.items() if v is not None}
    kvs = " ".join(f"{k}={v}" for k, v in context.items())
    message = f"{verb} | {kvs}" if kvs else verb
    fn = getattr(logger, level.lower(), logger.info)
    fn(message, event=event, **context)


def setup_logging(
    *,
    sink: TextIO | str | Path = sys.stderr,
    level: str = _LOG_LEVEL,
    format_: str = _LOG_FORMAT,
    log_path: TextIO | str | Path | None = None,
    verbose: int = 0,
    log_level_explicit: str | None = None,
    json_format: bool = False,
) -> int:
    """Configura o logger compartilhado, substituindo qualquer sink anterior.

    Seguro de chamar repetidamente: sempre remove os handlers anteriores, de
    modo que os sink nunca se acumulam. `verbose`/`log_level_explicit`/
    `json_format` implementam o ticket 05: `json_format` estrutura o stream
    (stderr) com `serialize=True` do loguru (uma linha JSON por registro, com
    `record.extra`); o arquivo de `log_path` permanece texto legível. Retorna o
    id do handler do console (que os testes podem querer remover).
    """
    level = resolve_log_level(verbose, log_level_explicit)

    logger.remove()
    if json_format:
        if isinstance(sink, (str, Path)):
            raise ValueError("--log-format json exige um sink file-like (ex.: stderr)")
        console_handler_id = logger.add(sink, level=level, serialize=True)
    else:
        console_handler_id = logger.add(sink, level=level, format=format_)

    if log_path is not None:
        if isinstance(log_path, (str, Path)):
            path = Path(log_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            logger.add(
                path,
                level=level,
                format=_FILE_LOG_FORMAT,
                encoding="utf-8",
                enqueue=False,
                retention=_LOG_RETENTION,
            )
        else:
            logger.add(log_path, level=level, format=_FILE_LOG_FORMAT)

    return console_handler_id


# Configuração no import; reentrante para testes via setup_logging().
setup_logging()
