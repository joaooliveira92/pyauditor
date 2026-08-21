"""`pyauditor split <competência> --orgao <MinC|MTur>` — materializes, per
(INMS, categoria) pair in `mode: grupo_executor` of `categorias.yaml` (spec
§14.2/§14.3), a filtered CSV and a derived indicator config so `measure`
(100% unchanged) discovers and measures each Categoria independently.

For each INMS with at least one `grupo_executor` entry:
- one CSV + derived config per categoria, at the exact paths ticket 03
  fixes: `input/<orgao>/<ano>/<mes>/_split/<inms>/<categoria>.csv` and
  `configs/<orgao>/inms-<n>.<categoria>.yaml` (the extra dot keeps it
  gitignored yet discovered by `measure`'s existing glob — see ADR 0002);
- one `outros.csv` (audit only, no derived config) for whatever
  `Grupo_executor` literal no categoria claims.

`mode: whole_indicator` INMS are skipped entirely — no artifact, the base
`inms-<n>.yaml` measures the whole dataset directly. `split` always
overwrites on rerun (idempotent by regeneration); the raw CSV is never
touched.

When *report_dir* (a reports base dir, `reports/<orgao>`) is given, `run_split`
also (re)writes `<report_dir>/<competencia>/sintetico.xlsx` (spec §14.4,
ticket 05) — see `excel/sintetico.py` for that report's own INMS-mode
coverage, which spans both `grupo_executor` and `whole_indicator`.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import yaml

from pyauditor.atomic_write import atomic_write
from pyauditor.categoria_filter import (
    GRUPO_EXECUTOR_COLUMN,
    base_config_stem,
    compute_categoria_values,
    read_raw_csv,
)
from pyauditor.cli.results import DependencyCheck, Status, validate_competencia
from pyauditor.config.categorias import GrupoExecutorMode, load_categorias
from pyauditor.config.manifest import DatasetManifest
from pyauditor.config.models import IndicatorConfig, Source
from pyauditor.engine.pipeline import load_config, resolve_source
from pyauditor.excel.sintetico import write_sintetico_workbook
from pyauditor.logging import log_event, logger
from pyauditor.periodo import (
    PeriodoAfericao,
    discard_message,
    empty_window_message,
    filter_periodo,
    require_period_column,
)

__all__: Final[tuple[str, ...]] = (
    "SplitCategoriaOutcome",
    "SplitResult",
    "check_split_ready",
    "run_split",
)

_SPLIT_DIRNAME: Final[str] = "_split"
_OUTROS_NAME: Final[str] = "outros"
_SINTETICO_FILENAME: Final[str] = "sintetico.xlsx"


@dataclass(frozen=True, slots=True)
class SplitCategoriaOutcome:
    inms: str
    categoria: str
    csv_path: Path
    config_path: Path | None  # None só para `outros` (sem config derivada)
    row_count: int


@dataclass(frozen=True, slots=True)
class SplitResult:
    status: Status
    competencia: str
    orgao: str
    categorias: tuple[SplitCategoriaOutcome, ...]
    warnings: tuple[str, ...]
    error_message: str | None


def check_split_ready(*_args: object, **_kwargs: object) -> DependencyCheck:
    """`split` só precisa de `categorias.yaml` + CSVs brutos, ambos entradas
    externas que ele mesmo valida — sem dependência de outro Command."""
    return DependencyCheck(satisfied=True, missing=())


def _write_filtered_csv(
    path: Path, fieldnames: list[str], rows: list[dict[str, str]], delimiter: str
) -> None:
    def _write(tmp_path: Path) -> None:
        with tmp_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=delimiter)
            writer.writeheader()
            writer.writerows(rows)

    atomic_write(path, _write)


def _derive_config(
    base: IndicatorConfig, categoria_key: str, csv_relpath: str, delimiter: str
) -> IndicatorConfig:
    """Copia `quality_gates`/`calculation`/`target`/`penalty` de *base*,
    trocando só `indicator.id` e `source` (nunca `source.dataset` — a config
    derivada aponta pro CSV filtrado direto, `split` não toca em
    `datasets.yaml`). `acceptance_test` (números do dataset inteiro) não se
    aplica ao subconjunto filtrado — omitido."""
    derived_indicator = base.indicator.model_copy(
        update={"id": f"{base.indicator.id}.{categoria_key}"}
    )
    derived_source = Source(
        csv=csv_relpath,
        delimiter=delimiter,
        encoding="utf-8",
        id_column=base.source.id_column,
        period_column=base.source.period_column,
    )
    return base.model_copy(
        update={
            "indicator": derived_indicator,
            "source": derived_source,
            "acceptance_test": None,
        }
    )


def _write_derived_config(path: Path, config: IndicatorConfig) -> None:
    raw = config.model_dump(mode="json", exclude_none=True)

    def _write(tmp_path: Path) -> None:
        tmp_path.write_text(
            yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )

    atomic_write(path, _write)


def run_split(
    competencia: str,
    config_dir: Path,
    data_dir: Path,
    *,
    expected_orgao: str,
    manifest: DatasetManifest | None = None,
    report_dir: Path | None = None,
    materialize: bool = True,
    periodo: PeriodoAfericao | None = None,
    strict: bool = False,
) -> SplitResult:
    orgao = expected_orgao

    def _error(message: str) -> SplitResult:
        logger.error(message)
        return SplitResult(
            status="error", competencia=competencia, orgao=orgao, categorias=(),
            warnings=(), error_message=message,
        )

    competencia_error = validate_competencia(competencia)
    if competencia_error is not None:
        return _error(competencia_error)

    # Datasets/artefatos de `split` vivem em <data-dir>/<YYYY>/<MM>, mesma
    # convenção por competência de `measure`.
    year, month = competencia.split("-")
    competencia_data_dir = data_dir / year / month

    # Single-source: `config_dir` pode ser `_shared` (sem categorias.yaml);
    # fallback para `config_dir.parent/<orgao>/categorias.yaml`.
    categorias_path = config_dir / "categorias.yaml"
    if not categorias_path.exists() and config_dir.name == "_shared":
        fallback = config_dir.parent / expected_orgao / "categorias.yaml"
        if fallback.exists():
            categorias_path = fallback
    try:
        categorias_file = load_categorias(categorias_path)
    except (OSError, ValueError) as exc:
        return _error(f"falha ao carregar {categorias_path}: {exc}")

    # Agrupa por INMS: quais categorias o reivindicam em modo grupo_executor
    # (whole_indicator não gera nenhum artefato — nem entra neste mapa).
    per_inms: dict[str, list[tuple[str, GrupoExecutorMode]]] = {}
    for categoria_key, categoria in categorias_file.categorias.items():
        for inms_key, entry in categoria.inms.items():
            if isinstance(entry, GrupoExecutorMode):
                per_inms.setdefault(inms_key, []).append((categoria_key, entry))

    warnings: list[str] = []
    outcomes: list[SplitCategoriaOutcome] = []
    any_error = False

    for inms_key in sorted(per_inms):
        entries = per_inms[inms_key]
        try:
            base_stem = base_config_stem(inms_key)
        except ValueError as exc:
            logger.error(str(exc))
            any_error = True
            continue

        base_config_path = config_dir / f"{base_stem}.yaml"
        try:
            base_config = load_config(base_config_path)
        except (OSError, ValueError) as exc:
            logger.error(
                f"INMS {inms_key} ({orgao}/{competencia}): falha ao carregar config base "
                f"{base_config_path}: {exc}"
            )
            any_error = True
            continue

        try:
            raw_csv_path, delimiter, encoding = resolve_source(
                base_config, competencia_data_dir, manifest
            )
        except ValueError as exc:
            logger.error(
                f"INMS {inms_key} ({orgao}/{competencia}): falha ao resolver fonte de dados: {exc}"
            )
            any_error = True
            continue

        try:
            fieldnames, rows = read_raw_csv(raw_csv_path, delimiter, encoding)
        except (OSError, ValueError) as exc:
            logger.error(
                f"INMS {inms_key} ({orgao}/{competencia}): falha ao ler {raw_csv_path}: {exc}"
            )
            any_error = True
            continue

        if GRUPO_EXECUTOR_COLUMN not in fieldnames:
            logger.error(
                f"INMS {inms_key} ({orgao}/{competencia}): {raw_csv_path} não tem coluna "
                f"'{GRUPO_EXECUTOR_COLUMN}' — declarado mode: grupo_executor em categorias.yaml"
            )
            any_error = True
            continue

        # Filtro de período (§2 ponto 1): logo após read_raw_csv, ANTES de
        # computar categorias — row_count/outros/warnings refletem o
        # pós-filtro. WARN de janela vazia: 1x por (órgão, arquivo bruto).
        if periodo is not None:
            try:
                period_column = require_period_column(
                    base_config.source.period_column, config_path=base_config_path
                )
            except ValueError as exc:
                logger.error(f"INMS {inms_key} ({orgao}/{competencia}): {exc}")
                any_error = True
                continue
            total_bruto = len(rows)
            filtro = filter_periodo(
                rows, period_column=period_column, periodo=periodo, strict=strict
            )
            rows = filtro.linhas_na_janela
            if total_bruto > 0 and not rows:
                aviso_vazio = (
                    f"INMS {inms_key} ({orgao}/{competencia}): "
                    f"{empty_window_message(periodo)}"
                )
                log_event(
                    "periodo_janela_vazia",
                    aviso_vazio,
                    "WARNING",
                    orgao=orgao,
                    competencia=competencia,
                    inms=inms_key,
                    arquivo=str(raw_csv_path),
                )
                warnings.append(aviso_vazio)
            info_descarte = discard_message(
                filtro.dropped_out_of_period, filtro.undated_dropped, strict
            )
            if info_descarte is not None:
                log_event(
                    "periodo_filtro",
                    f"INMS {inms_key} ({orgao}/{competencia}): {info_descarte}",
                    "INFO",
                    orgao=orgao,
                    competencia=competencia,
                    inms=inms_key,
                    arquivo=str(raw_csv_path),
                    descartadas=filtro.dropped_out_of_period,
                    sem_data=filtro.undated_dropped,
                )

        real_values = {row[GRUPO_EXECUTOR_COLUMN] for row in rows}
        # Cross-check in_values contra valores reais (issue 09): typo/renomeação
        # no CSV gera categoria sem linhas — indistinguível de zero atividade
        for categoria_key, entry in entries:
            if entry.in_values is not None:
                unmatched = [v for v in entry.in_values if v not in real_values]
                if unmatched and not (set(entry.in_values) & real_values):
                    warning = (
                        f"INMS {inms_key} ({orgao}/{competencia}), categoria {categoria_key}: "
                        f"in_values {unmatched!r} sem correspondência em Grupo_executor do CSV "
                        f"({raw_csv_path}) — possível typo/renomeação, categoria ficará sem linhas"
                    )
                    logger.warning(warning)
                    warnings.append(warning)
                elif unmatched:
                    warning = (
                        f"INMS {inms_key} ({orgao}/{competencia}), categoria {categoria_key}: "
                        f"in_values {unmatched!r} sem correspondência — "
                        "valores não encontrados no CSV"
                    )
                    logger.warning(warning)
                    warnings.append(warning)
        per_categoria_values, outros_values = compute_categoria_values(entries, real_values)

        split_dir = competencia_data_dir / _SPLIT_DIRNAME / inms_key

        for categoria_key, effective_values in per_categoria_values.items():
            filtered_rows = [
                row for row in rows if row[GRUPO_EXECUTOR_COLUMN] in effective_values
            ]
            csv_path = split_dir / f"{categoria_key}.csv"
            if materialize:
                try:
                    _write_filtered_csv(csv_path, fieldnames, filtered_rows, delimiter)
                except OSError as exc:
                    logger.error(f"falha ao escrever {csv_path}: {exc}")
                    any_error = True
                    continue

            csv_relpath = f"{_SPLIT_DIRNAME}/{inms_key}/{categoria_key}.csv"
            derived_config = _derive_config(base_config, categoria_key, csv_relpath, delimiter)
            # Single-source: derivados vivem no dir per-órgão, não em _shared
            derived_dir = config_dir
            if config_dir.name == "_shared":
                derived_dir = config_dir.parent / expected_orgao
            config_path = derived_dir / f"{base_stem}.{categoria_key}.yaml"
            if materialize:
                try:
                    _write_derived_config(config_path, derived_config)
                except OSError as exc:
                    logger.error(f"falha ao escrever {config_path}: {exc}")
                    any_error = True
                    continue
            else:
                # Sem materialização: config_path fica None semanticamente,
                # mas mantemos o path para rastreabilidade no outcome.
                config_path = None  # type: ignore[assignment]

            outcomes.append(SplitCategoriaOutcome(
                inms=inms_key, categoria=categoria_key, csv_path=csv_path,
                config_path=config_path,
                row_count=len(filtered_rows),
            ))

        outros_rows = [row for row in rows if row[GRUPO_EXECUTOR_COLUMN] in outros_values]
        outros_path = split_dir / f"{_OUTROS_NAME}.csv"
        if materialize:
            try:
                _write_filtered_csv(outros_path, fieldnames, outros_rows, delimiter)
            except OSError as exc:
                logger.error(f"falha ao escrever {outros_path}: {exc}")
                any_error = True
                continue
        else:
            # Sem materialização: ainda conta para warning, mas não escreve
            pass

        outcomes.append(SplitCategoriaOutcome(
            inms=inms_key, categoria=_OUTROS_NAME, csv_path=outros_path,
            config_path=None, row_count=len(outros_rows),
        ))
        if outros_rows:
            warning = (
                f"INMS {inms_key} ({orgao}/{competencia}), categoria outros: "
                f"{len(outros_rows)} linha(s) não classificada(s) em nenhuma categoria — "
                "revisar categorias.yaml"
            )
            logger.warning(warning)
            warnings.append(warning)

    # sintetico.xlsx (spec §14.4, ticket 05): uma aba por INMS com entrada em
    # categorias.yaml, para os dois modes — cobre bem mais INMS do que o
    # laço acima (que só materializa artefatos para `grupo_executor`).
    # `report_dir` é opcional (`None` pula a geração) para não obrigar todo
    # chamador existente de `run_split` a passar um diretório de relatórios.
    if report_dir is not None:
        sintetico_path = report_dir / competencia / _SINTETICO_FILENAME
        try:
            sintetico_warnings = write_sintetico_workbook(
                categorias_file, config_dir, competencia_data_dir, sintetico_path,
                manifest=manifest, periodo=periodo, strict=strict,
            )
            warnings.extend(sintetico_warnings)
        except OSError as exc:
            warning = f"falha ao escrever {sintetico_path}: {exc}"
            logger.warning(warning)
            warnings.append(warning)

    log_event(
        "split_done",
        f"{orgao or 'órgão'}: {len(outcomes)} categoria(s) processada(s)",
        "INFO",
        orgao=orgao,
        competencia=competencia,
        status="error" if any_error else "done",
    )

    error_message = "uma ou mais categorias tiveram falha em split" if any_error else None
    return SplitResult(
        status="error" if any_error else "done",
        competencia=competencia,
        orgao=orgao,
        categorias=tuple(outcomes),
        warnings=tuple(warnings),
        error_message=error_message,
    )
