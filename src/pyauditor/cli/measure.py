"""`pyauditor measure <competência>` — run every configured indicator, write one
ROM Markdown per indicator, report hard failures (spec §4/§6).

Alongside each `<indicator.id>.md` ROM, also writes a `<indicator.id>.json`
structured summary (see `rom/summary.py`) — `report` (ticket 09) reads these
JSON sidecars rather than re-parsing the ROM's prose Markdown.

Datasets are organized per competência: `measure 2026-06 --data-dir input`
reads every CSV from `input/2026/06/` (derived from the competência, never
from the data-dir root). Keeping each competência in its own folder lets one
project hold the data of every past aferição side by side.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pyauditor.cli.results import DependencyCheck, Status, validate_competencia
from pyauditor.config.manifest import DatasetManifest
from pyauditor.engine.pipeline import discover_config_files, measure
from pyauditor.excel.capa import read_capa_fields
from pyauditor.logging import logger
from pyauditor.rom.render import render_rom
from pyauditor.rom.summary import summarize

_UNSAFE_ID_CHARS_RE: Final = re.compile(r"[^A-Za-z0-9._-]")


@dataclass(frozen=True, slots=True)
class IndicatorOutcome:
    contractual_id: str
    rom_path: Path
    summary_path: Path
    hard_failure: bool
    error: str | None


@dataclass(frozen=True, slots=True)
class MeasureResult:
    status: Status
    competencia: str
    orgao: str
    indicators: tuple[IndicatorOutcome, ...]
    warnings: tuple[str, ...]
    error_message: str | None


def check_measure_ready(*_args: object, **_kwargs: object) -> DependencyCheck:
    """`measure` only needs configs+data, both external inputs it validates
    itself — no dependency on another Command's output."""
    return DependencyCheck(satisfied=True, missing=())

# Capa labels the ROM's Identificação/Responsáveis sections read (rom/render.py).
_CAPA_ROM_FIELDS: Final[tuple[str, ...]] = (
    "Competência",
    "Período inicial da aferição",
    "Período final da aferição",
    "Fiscal técnico",
    "Fiscal requisitante",
    "Fiscal administrativo",
    "Gestor do contrato",
)


def _sanitize_indicator_id(raw: str) -> str:
    """Filesystem-safe ROM filename stem — never traverses out of the output dir."""
    sanitized = _UNSAFE_ID_CHARS_RE.sub("_", raw).strip("._")
    return sanitized or "_indicator"


def run_measure(
    competencia: str,
    config_dir: Path,
    data_dir: Path,
    output_dir: Path,
    manifest: DatasetManifest | None = None,
    *,
    expected_orgao: str | None = None,
    capa_path: Path | None = None,
) -> MeasureResult:
    orgao = expected_orgao or ""

    def _error(message: str) -> MeasureResult:
        logger.error(message)
        return MeasureResult(
            status="error", competencia=competencia, orgao=orgao, indicators=(),
            warnings=(), error_message=message,
        )

    competencia_error = validate_competencia(competencia)
    if competencia_error is not None:
        return _error(competencia_error)

    # Datasets live under <data-dir>/<YYYY>/<MM> for this competência — never
    # at the data-dir root — so past aferições can coexist in the same project.
    year, month = competencia.split("-")
    competencia_data_dir = data_dir / year / month

    try:
        configs = discover_config_files(config_dir, expected_orgao=expected_orgao)
    except (OSError, ValueError) as exc:
        return _error(f"falha ao carregar configs de {config_dir}: {exc}")
    if not configs:
        return _error(f"nenhum config encontrado em {config_dir}")

    target_dir = output_dir / competencia
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return _error(f"falha ao criar diretório {target_dir}: {exc}")

    # Identificação/Responsáveis in the ROM come from the capa — informational
    # only here (unlike `report`'s "Valor mensal vigente", nothing here blocks
    # the measurement), so a missing capa is a warning, not a hard failure.
    capa_fields: dict[str, object] = {}
    warnings: list[str] = []
    if capa_path is not None:
        if capa_path.exists():
            capa_fields = read_capa_fields(capa_path)
            empty_fields = [f for f in _CAPA_ROM_FIELDS if not capa_fields.get(f)]
            if empty_fields:
                warning = (
                    f"capa em {capa_path} sem preencher: {', '.join(empty_fields)} — "
                    "ROM mostra '[a preencher]' nesses campos"
                )
                logger.warning(warning)
                warnings.append(warning)
        else:
            warning = (
                f"capa não encontrada em {capa_path} — identificação/responsáveis do ROM "
                "ficam '[a preencher]'"
            )
            logger.warning(warning)
            warnings.append(warning)

    any_hard_failure = False
    outcomes: list[IndicatorOutcome] = []

    for config_path, config_hash, config in configs:
        contractual_id = config.indicator.contractual_id
        safe_id = _sanitize_indicator_id(config.indicator.id)
        rom_path = target_dir / f"{safe_id}.md"
        summary_path = target_dir / f"{safe_id}.json"

        try:
            result = measure(
                config,
                data_dir=competencia_data_dir,
                manifest=manifest,
                config_path=config_path,
                config_hash=config_hash,
            )
            rom_path.write_text(render_rom(result, capa_fields=capa_fields), encoding="utf-8")
            summary_path.write_text(
                json.dumps(summarize(result).to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            message = f"falha ao escrever {rom_path}: {exc}"
            logger.error(message)
            any_hard_failure = True
            outcomes.append(IndicatorOutcome(
                contractual_id=contractual_id, rom_path=rom_path, summary_path=summary_path,
                hard_failure=True, error=message,
            ))
            continue
        # Broad by design — isolates one indicator's failure so the rest of the
        # batch still measures (bootstrap.py/report.py/consolidate.py catch
        # broadly too, but abort the whole command — this one deliberately
        # doesn't, since a batch of indicators shouldn't die together).
        except Exception as exc:
            message = f"{contractual_id}: exceção na medição: {exc}"
            logger.error(message)
            any_hard_failure = True
            outcomes.append(IndicatorOutcome(
                contractual_id=contractual_id, rom_path=rom_path, summary_path=summary_path,
                hard_failure=True, error=message,
            ))
            continue

        if result.hard_failure:
            any_hard_failure = True
            error = (
                f"{contractual_id}: falha de medição — "
                f"nenhuma linha sobreviveu aos quality gates ({rom_path})"
            )
            logger.error(error)
            outcomes.append(IndicatorOutcome(
                contractual_id=contractual_id, rom_path=rom_path, summary_path=summary_path,
                hard_failure=True, error=error,
            ))
        else:
            logger.info(f"{contractual_id}: {rom_path}")
            outcomes.append(IndicatorOutcome(
                contractual_id=contractual_id, rom_path=rom_path, summary_path=summary_path,
                hard_failure=False, error=None,
            ))

    error_message = (
        "um ou mais indicadores tiveram falha de medição" if any_hard_failure else None
    )
    return MeasureResult(
        status="error" if any_hard_failure else "done",
        competencia=competencia,
        orgao=orgao,
        indicators=tuple(outcomes),
        warnings=tuple(warnings),
        error_message=error_message,
    )
