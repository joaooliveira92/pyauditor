"""`pyauditor measure <competência>` — run every configured indicator, write one
ROM Markdown per indicator, report hard failures (spec §4/§6).

Alongside each `<indicator.id>.md` ROM, also writes a `<indicator.id>.json`
structured summary (see `rom/summary.py`) — `report` (ticket 09) reads these
JSON sidecars rather than re-parsing the ROM's prose Markdown.
"""

import json
import re
from pathlib import Path
from typing import Final

from pyauditor.engine.pipeline import discover_configs, measure
from pyauditor.logging import logger
from pyauditor.rom.render import render_rom
from pyauditor.rom.summary import summarize

_COMPETENCIA_RE: Final = re.compile(r"^\d{4}-\d{2}$")
_UNSAFE_ID_CHARS_RE: Final = re.compile(r"[^A-Za-z0-9._-]")


def _sanitize_indicator_id(raw: str) -> str:
    """Filesystem-safe ROM filename stem — never traverses out of the output dir."""
    sanitized = _UNSAFE_ID_CHARS_RE.sub("_", raw).strip("._")
    return sanitized or "_indicator"


def run_measure(competencia: str, config_dir: Path, data_dir: Path, output_dir: Path) -> int:
    if not _COMPETENCIA_RE.match(competencia):
        logger.error(f"competência inválida {competencia!r}: esperado YYYY-MM (ex.: 2026-06)")
        return 1

    configs = discover_configs(config_dir)
    if not configs:
        logger.error(f"nenhum config encontrado em {config_dir}")
        return 1

    target_dir = output_dir / competencia
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.error(f"falha ao criar diretório {target_dir}: {exc}")
        return 1

    any_hard_failure = False

    for config in configs:
        contractual_id = config.indicator.contractual_id
        safe_id = _sanitize_indicator_id(config.indicator.id)
        rom_path = target_dir / f"{safe_id}.md"
        summary_path = target_dir / f"{safe_id}.json"

        try:
            result = measure(config, data_dir=data_dir)
            rom_path.write_text(render_rom(result), encoding="utf-8")
            summary_path.write_text(
                json.dumps(summarize(result).to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.error(f"falha ao escrever {rom_path}: {exc}")
            any_hard_failure = True
            continue
        except Exception as exc:  # noqa: BLE001 — boundary: log and keep processing other indicators
            logger.error(f"{contractual_id}: exceção na medição: {exc}")
            any_hard_failure = True
            continue

        if result.hard_failure:
            any_hard_failure = True
            logger.error(
                f"{contractual_id}: falha de medição — "
                f"nenhuma linha sobreviveu aos quality gates ({rom_path})"
            )
        else:
            logger.info(f"{contractual_id}: {rom_path}")

    return 1 if any_hard_failure else 0
