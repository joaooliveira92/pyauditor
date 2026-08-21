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
from typing import Final, cast

from pyauditor.cli.results import (
    DIR_FAILURE_HINT,
    WRITE_FAILURE_HINT,
    DependencyCheck,
    Status,
    validate_competencia,
)
from pyauditor.config.manifest import DatasetManifest
from pyauditor.engine.pipeline import (
    MeasurementResult,
    discover_config_files,
    measure,
)
from pyauditor.excel.capa import read_capa_csv_fields
from pyauditor.logging import log_event, logger
from pyauditor.rom.render import render_combined_rom, render_rom
from pyauditor.rom.summary import summarize

_UNSAFE_ID_CHARS_RE: Final = re.compile(r"[^A-Za-z0-9._-]")


@dataclass(frozen=True, slots=True)
class IndicatorOutcome:
    contractual_id: str
    rom_path: Path
    summary_path: Path
    hard_failure: bool
    error: str | None
    # Dataset ausente para a competência (spec §14.1) — não é falha, mas
    # também não é "medido com população zero" (report/xlsx precisam
    # distinguir os dois estados: ticket 02 do tracker inms-categoria-split).
    not_activated: bool = False


@dataclass(frozen=True, slots=True)
class MeasureResult:
    status: Status
    competencia: str
    orgao: str
    indicators: tuple[IndicatorOutcome, ...]
    warnings: tuple[str, ...]
    error_message: str | None


@dataclass(frozen=True, slots=True)
class _MeasuredIndicator:
    """A measured indicator alongside enough to render the combined markdown
    later — `result` (the numbers) and the capa fields used for its orgão."""

    indicator_id: str
    safe_id: str
    orgao: str
    result: MeasurementResult
    capa_fields: dict[str, object]


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
    collect: list[_MeasuredIndicator] | None = None,
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
        return _error(f"falha ao criar diretório {target_dir}: {exc} — {DIR_FAILURE_HINT}")

    # Identificação/Responsáveis in the ROM come from the capa — informational
    # only here (unlike `report`'s "Valor mensal vigente", nothing here blocks
    # the measurement), so a missing capa is a warning, not a hard failure.
    capa_fields: dict[str, object] = {}
    warnings: list[str] = []
    if capa_path is not None:
        if capa_path.exists():
            try:
                capa_fields = cast(dict[str, object], read_capa_csv_fields(capa_path))
            except (OSError, ValueError) as exc:
                warning = (
                    f"falha ao ler capa em {capa_path}: {exc} — "
                    "identificação/responsáveis do ROM ficam '[a preencher]'"
                )
                logger.warning(warning)
                warnings.append(warning)
                capa_fields = {}
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
        # Dataset ausente na competência (spec §14.1): não é falha de quality
        # gate nem erro — o elemento contratual não foi demandado/ativado no
        # período. Vale para os 14 indicadores, não só os de categoria.
        except FileNotFoundError:
            warning = (
                f"{contractual_id} ({config.scope.orgao}/{competencia}): não ativado — "
                "dataset ausente (serviço não requisitado no período)"
            )
            logger.warning(warning)
            warnings.append(warning)
            outcomes.append(IndicatorOutcome(
                contractual_id=contractual_id, rom_path=rom_path, summary_path=summary_path,
                hard_failure=False, error=None, not_activated=True,
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

        try:
            rom_path.write_text(render_rom(result, capa_fields=capa_fields), encoding="utf-8")
            summary = summarize(result)
            summary_path.write_text(
                json.dumps(summary.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            message = f"falha ao escrever {rom_path}: {exc} — {WRITE_FAILURE_HINT}"
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
        elif getattr(result, "systematic_failure", False):
            any_hard_failure = True
            error = (
                f"{contractual_id}: não-conformidade sistemática — "
                f"resultado {summary.result_pct:.2f}% sempre não-conforme, "
                f"possível bug de cálculo ({rom_path})"
            )
            logger.error(error)
            outcomes.append(IndicatorOutcome(
                contractual_id=contractual_id, rom_path=rom_path, summary_path=summary_path,
                hard_failure=True, error=error,
            ))
        else:
            # Observabilidade (ticket 05, Q2/Q7): sem linha por indicador no
            # padrão (INFO); com `-v`/`-vv` (DEBUG) um evento por indicador.
            status_label = "conforme" if getattr(summary, "conforms", True) else "nao_conforme"
            if getattr(summary, "systematic_failure", False):
                status_label = "nao_conforme_sistematica"
            log_event(
                "indicator_measured",
                "indicador apurado",
                "DEBUG",
                orgao=orgao or "",
                codigo=contractual_id,
                rom_path=str(rom_path),
                status=status_label,
            )
            outcomes.append(IndicatorOutcome(
                contractual_id=contractual_id, rom_path=rom_path, summary_path=summary_path,
                hard_failure=False, error=None,
            ))

        if collect is not None:
            collect.append(_MeasuredIndicator(
                indicator_id=config.indicator.id,
                safe_id=safe_id,
                orgao=config.scope.orgao,
                result=result,
                capa_fields=capa_fields,
            ))

    # Resumo conciso por órgão (INFO) — no lugar das N linhas repetidas.
    total = len(outcomes)
    ok = sum(1 for o in outcomes if not o.hard_failure)
    log_event(
        "measure_done",
        f"{orgao or 'órgão'}: {ok}/{total} indicador(es) apurado(s)",
        "INFO",
        orgao=orgao,
        competencia=competencia,
        status="error" if any_hard_failure else "done",
    )

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


def write_combined_roms(
    per_orgao: dict[str, list[_MeasuredIndicator]], competencia: str, output_dir: Path
) -> None:
    """Given the measured indicators of each orgão (from `run_measure(...,
    collect=...)` calls with `--orgao both`), write under
    `output_dir/both/<competencia>/` one markdown per indicator with both
    orgãos' ROMs stacked. Skips indicators that only measured in one orgão
    (warning, no combined render without the pair)."""
    both_dir = output_dir / "both" / competencia
    both_dir.mkdir(parents=True, exist_ok=True)

    by_id: dict[str, dict[str, _MeasuredIndicator]] = {}
    for orgao, measured in per_orgao.items():
        for item in measured:
            by_id.setdefault(item.indicator_id, {})[orgao] = item

    for indicator_id, orgs in sorted(by_id.items()):
        if len(orgs) < 2:
            missing = ", ".join(sorted({"MinC", "MTur"} - set(orgs)))
            logger.warning(
                f"{indicator_id}: ROM combinado 'both' não gerado — falta medição de {missing}"
            )
            continue

        minc = orgs["MinC"]
        mtur = orgs["MTur"]
        capa_by_orgao = {"MinC": minc.capa_fields, "MTur": mtur.capa_fields}
        combined_path = both_dir / f"{minc.safe_id}.md"
        try:
            combined_path.write_text(
                render_combined_rom(minc.result, mtur.result, capa_by_orgao),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.error(f"falha ao escrever {combined_path}: {exc} — {WRITE_FAILURE_HINT}")
