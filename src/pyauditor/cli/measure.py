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

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final, cast

from pyauditor.categoria_filter import (
    GRUPO_EXECUTOR_COLUMN,
    compute_categoria_values,
    read_raw_csv,
)
from pyauditor.cli.results import (
    DIR_FAILURE_HINT,
    WRITE_FAILURE_HINT,
    DependencyCheck,
    Status,
    validate_competencia,
)
from pyauditor.config.categorias import GrupoExecutorMode, load_categorias
from pyauditor.config.manifest import DatasetManifest
from pyauditor.engine.pipeline import (
    MeasurementProvenance,
    MeasurementResult,
    _pipeline_version,
    discover_config_files,
    measure,
    resolve_source,
)
from pyauditor.engine.quality_gates import QualityGateRunner
from pyauditor.engine.strategies import SHAPE_REGISTRY
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


def _inms_key_from_contractual_id(contractual_id: str) -> str | None:
    """`INMS 1.1` -> `1.1` — chave usada em `categorias.yaml`."""
    parts = contractual_id.strip().split()
    if not parts:
        return None
    last = parts[-1]
    # Valida formato 1.N
    if "." not in last:
        return None
    return last


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

    # Single-source categorias: carrega uma vez por execução (fallback para
    # parent/<orgao>/categorias.yaml quando config_dir é _shared).
    categorias_file = None
    per_inms: dict[str, list[tuple[str, GrupoExecutorMode]]] = {}
    if expected_orgao is not None:
        categorias_path = config_dir / "categorias.yaml"
        if not categorias_path.exists() and config_dir.name == "_shared":
            fallback = config_dir.parent / expected_orgao / "categorias.yaml"
            if fallback.exists():
                categorias_path = fallback
        if categorias_path.exists():
            try:
                categorias_file = load_categorias(categorias_path)
                for cat_key, cat in categorias_file.categorias.items():
                    for cat_inms_key, entry in cat.inms.items():
                        if isinstance(entry, GrupoExecutorMode):
                            per_inms.setdefault(cat_inms_key, []).append((cat_key, entry))
            except (OSError, ValueError) as exc:
                logger.warning(f"falha ao carregar categorias {categorias_path}: {exc}")

    any_hard_failure = False
    outcomes: list[IndicatorOutcome] = []

    def _handle_result(
        result: MeasurementResult,
        safe_id: str,
        rom_path: Path,
        summary_path: Path,
        contractual_id: str,
        indicator_id: str,
        scope_orgao: str,
    ) -> None:
        nonlocal any_hard_failure
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
            return
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
            error2 = (
                f"{contractual_id}: não-conformidade sistemática — "
                f"resultado {summary.result_pct:.2f}% sempre não-conforme, "
                f"possível bug de cálculo ({rom_path})"
            )
            logger.error(error2)
            outcomes.append(IndicatorOutcome(
                contractual_id=contractual_id, rom_path=rom_path, summary_path=summary_path,
                hard_failure=True, error=error2,
            ))
        else:
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
                indicator_id=indicator_id,
                safe_id=safe_id,
                orgao=scope_orgao,
                result=result,
                capa_fields=capa_fields,
            ))

    for config_path, config_hash, config in configs:
        contractual_id = config.indicator.contractual_id
        inms_key: str | None = _inms_key_from_contractual_id(contractual_id)
        entries = per_inms.get(inms_key) if inms_key is not None else None

        # Ticket 04 — filtro em memória: quando há categorias grupo_executor
        # para este INMS, expande em N medições filtradas sem materializar
        # _split/*. O caminho single (abaixo) só roda para whole_indicator.
        if entries is not None and categorias_file is not None:
            # Tenta resolver fonte bruta uma vez para todas as categorias
            try:
                raw_csv_path, delimiter, encoding = resolve_source(
                    config, competencia_data_dir, manifest
                )
            except FileNotFoundError:
                for cat_key, _ in entries:
                    derived_id = f"{config.indicator.id}.{cat_key}"
                    safe_id = _sanitize_indicator_id(derived_id)
                    rom_path = target_dir / f"{safe_id}.md"
                    summary_path = target_dir / f"{safe_id}.json"
                    warning = (
                        f"{contractual_id} ({config.scope.orgao}/{competencia}, {cat_key}): "
                        "não ativado — dataset ausente"
                    )
                    logger.warning(warning)
                    warnings.append(warning)
                    outcomes.append(IndicatorOutcome(
                        contractual_id=contractual_id, rom_path=rom_path,
                        summary_path=summary_path, hard_failure=False, error=None,
                        not_activated=True,
                    ))
                continue
            except Exception as exc:
                message = f"{contractual_id}: exceção na medição: {exc}"
                logger.error(message)
                any_hard_failure = True
                for cat_key, _ in entries:
                    derived_id = f"{config.indicator.id}.{cat_key}"
                    safe_id = _sanitize_indicator_id(derived_id)
                    rom_path = target_dir / f"{safe_id}.md"
                    summary_path = target_dir / f"{safe_id}.json"
                    outcomes.append(IndicatorOutcome(
                        contractual_id=contractual_id, rom_path=rom_path,
                        summary_path=summary_path, hard_failure=True, error=message,
                    ))
                continue
            try:
                fieldnames, rows = read_raw_csv(raw_csv_path, delimiter, encoding)
            except (OSError, ValueError) as exc:
                message = f"{contractual_id}: exceção na medição: {exc}"
                logger.error(message)
                any_hard_failure = True
                for cat_key, _ in entries:
                    derived_id = f"{config.indicator.id}.{cat_key}"
                    safe_id = _sanitize_indicator_id(derived_id)
                    rom_path = target_dir / f"{safe_id}.md"
                    summary_path = target_dir / f"{safe_id}.json"
                    outcomes.append(IndicatorOutcome(
                        contractual_id=contractual_id, rom_path=rom_path,
                        summary_path=summary_path, hard_failure=True, error=message,
                    ))
                continue
            if GRUPO_EXECUTOR_COLUMN not in fieldnames:
                message = (
                    f"{contractual_id}: exceção na medição: {raw_csv_path} não tem coluna "
                    f"'{GRUPO_EXECUTOR_COLUMN}' — declarado mode: grupo_executor em categorias.yaml"
                )
                logger.error(message)
                any_hard_failure = True
                for cat_key, _ in entries:
                    derived_id = f"{config.indicator.id}.{cat_key}"
                    safe_id = _sanitize_indicator_id(derived_id)
                    rom_path = target_dir / f"{safe_id}.md"
                    summary_path = target_dir / f"{safe_id}.json"
                    outcomes.append(IndicatorOutcome(
                        contractual_id=contractual_id, rom_path=rom_path,
                        summary_path=summary_path, hard_failure=True, error=message,
                    ))
                continue
            real_values = {row[GRUPO_EXECUTOR_COLUMN] for row in rows}
            for cat_key, entry in entries:
                if entry.in_values is not None:
                    unmatched = [v for v in entry.in_values if v not in real_values]
                    if unmatched and not (set(entry.in_values) & real_values):
                        w = (
                            f"INMS {inms_key} ({config.scope.orgao}/{competencia}), categoria {cat_key}: "
                            f"in_values {unmatched!r} sem correspondência em Grupo_executor do CSV "
                            f"({raw_csv_path}) — possível typo/renomeação, categoria ficará sem linhas"
                        )
                        logger.warning(w)
                        warnings.append(w)
                    elif unmatched:
                        w = (
                            f"INMS {inms_key} ({config.scope.orgao}/{competencia}), categoria {cat_key}: "
                            f"in_values {unmatched!r} sem correspondência — valores não encontrados no CSV"
                        )
                        logger.warning(w)
                        warnings.append(w)
            per_categoria_values, outros_values = compute_categoria_values(entries, real_values)
            # mede cada categoria filtrada em memória
            for cat_key, effective_values in per_categoria_values.items():
                filtered_rows = [r for r in rows if r[GRUPO_EXECUTOR_COLUMN] in effective_values]
                derived_indicator = config.indicator.model_copy(update={"id": f"{config.indicator.id}.{cat_key}"})
                derived_config = config.model_copy(update={"indicator": derived_indicator, "acceptance_test": None})
                derived_safe_id = _sanitize_indicator_id(derived_config.indicator.id)
                rom_path = target_dir / f"{derived_safe_id}.md"
                summary_path = target_dir / f"{derived_safe_id}.json"
                # quality gates + estratégia sobre linhas filtradas
                try:
                    gate_runner = QualityGateRunner(derived_config.quality_gates.checks, id_column=derived_config.source.id_column)
                    gate_report = gate_runner.run(filtered_rows)
                    strategy = SHAPE_REGISTRY[derived_config.calculation.shape]
                    calculation = strategy.calculate(derived_config, gate_report.accepted)
                    csv_hash = hashlib.sha256(raw_csv_path.read_bytes()).hexdigest()
                    derived_hash = hashlib.sha256(
                        json.dumps(derived_config.model_dump(mode="json"), sort_keys=True).encode()
                    ).hexdigest()
                    provenance = MeasurementProvenance(
                        config_path=config_path,
                        config_hash=derived_hash,
                        csv_path=raw_csv_path,
                        csv_hash=csv_hash,
                        delimiter=delimiter,
                        encoding=encoding,
                        processed_at=datetime.now(),
                        pipeline_version=_pipeline_version(),
                    )
                    result = MeasurementResult(
                        config=derived_config, quality_gate_report=gate_report,
                        calculation=calculation, provenance=provenance,
                    )
                except Exception as exc:
                    message = f"{contractual_id}.{cat_key}: exceção na medição: {exc}"
                    logger.error(message)
                    any_hard_failure = True
                    outcomes.append(IndicatorOutcome(
                        contractual_id=contractual_id, rom_path=rom_path, summary_path=summary_path,
                        hard_failure=True, error=message,
                    ))
                    continue
                _handle_result(result, derived_safe_id, rom_path, summary_path, contractual_id, derived_config.indicator.id, derived_config.scope.orgao)
            # outros contábil — warning se houver linhas não classificadas
            outros_rows = [r for r in rows if r[GRUPO_EXECUTOR_COLUMN] in outros_values]
            if outros_rows:
                w = (
                    f"INMS {inms_key} ({config.scope.orgao}/{competencia}), categoria outros: "
                    f"{len(outros_rows)} linha(s) não classificada(s) em nenhuma categoria — revisar categorias.yaml"
                )
                logger.warning(w)
                warnings.append(w)
            continue

        # Caminho single — whole_indicator ou INMS sem categoria grupo_executor
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
        except FileNotFoundError:
            _orgao_warn = getattr(getattr(config, "scope", None), "orgao", orgao)
            warning = (
                f"{contractual_id} ({_orgao_warn}/{competencia}): não ativado — "
                "dataset ausente (serviço não requisitado no período)"
            )
            logger.warning(warning)
            warnings.append(warning)
            outcomes.append(IndicatorOutcome(
                contractual_id=contractual_id, rom_path=rom_path, summary_path=summary_path,
                hard_failure=False, error=None, not_activated=True,
            ))
            continue
        except Exception as exc:
            message = f"{contractual_id}: exceção na medição: {exc}"
            logger.error(message)
            any_hard_failure = True
            outcomes.append(IndicatorOutcome(
                contractual_id=contractual_id, rom_path=rom_path, summary_path=summary_path,
                hard_failure=True, error=message,
            ))
            continue

        _handle_result(result, safe_id, rom_path, summary_path, contractual_id, config.indicator.id, getattr(getattr(config, "scope", None), "orgao", orgao))

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
