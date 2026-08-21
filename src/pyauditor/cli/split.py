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
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import yaml

from pyauditor.atomic_write import atomic_write
from pyauditor.cli.results import DependencyCheck, Status, validate_competencia
from pyauditor.config.categorias import GrupoExecutorMode, load_categorias
from pyauditor.config.manifest import DatasetManifest
from pyauditor.config.models import IndicatorConfig, Source
from pyauditor.engine.pipeline import load_config, resolve_source
from pyauditor.logging import log_event, logger

__all__: Final[tuple[str, ...]] = (
    "SplitCategoriaOutcome",
    "SplitResult",
    "check_split_ready",
    "run_split",
)

_SPLIT_DIRNAME: Final[str] = "_split"
_OUTROS_NAME: Final[str] = "outros"
_GRUPO_EXECUTOR_COLUMN: Final[str] = "Grupo_executor"
_INMS_KEY_RE: Final = re.compile(r"^1\.(\d+)$")


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


def _base_config_stem(inms_key: str) -> str:
    """`"1.7"` -> `"inms-07"` — mesma convenção de `inms-<n>.yaml` já usada
    pelos configs base (`configs/<orgao>/inms-NN.yaml`)."""
    match = _INMS_KEY_RE.match(inms_key)
    if match is None:
        raise ValueError(
            f"chave INMS inesperada em categorias.yaml: {inms_key!r} (esperado '1.<n>')"
        )
    return f"inms-{int(match.group(1)):02d}"


def _read_raw_csv(
    path: Path, delimiter: str, encoding: str
) -> tuple[list[str], list[dict[str, str]]]:
    """Como `engine.pipeline.load_rows`, mas também devolve os nomes de
    coluna — `split` precisa deles pra gravar `outros.csv` com cabeçalho
    mesmo quando o CSV bruto não tem nenhuma linha."""
    with path.open(encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: CSV vazio ou sem linha de cabeçalho")
        fieldnames = [name.strip() for name in reader.fieldnames]
        reader.fieldnames = fieldnames
        rows = [
            {name: (row.get(name) or "").strip() for name in fieldnames} for row in reader
        ]
    return fieldnames, rows


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

    categorias_path = config_dir / "categorias.yaml"
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
            base_stem = _base_config_stem(inms_key)
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
            fieldnames, rows = _read_raw_csv(raw_csv_path, delimiter, encoding)
        except (OSError, ValueError) as exc:
            logger.error(
                f"INMS {inms_key} ({orgao}/{competencia}): falha ao ler {raw_csv_path}: {exc}"
            )
            any_error = True
            continue

        if _GRUPO_EXECUTOR_COLUMN not in fieldnames:
            logger.error(
                f"INMS {inms_key} ({orgao}/{competencia}): {raw_csv_path} não tem coluna "
                f"'{_GRUPO_EXECUTOR_COLUMN}' — declarado mode: grupo_executor em categorias.yaml"
            )
            any_error = True
            continue

        real_values = {row[_GRUPO_EXECUTOR_COLUMN] for row in rows}
        in_values_claimed: set[str] = set()
        for _categoria_key, entry in entries:
            if entry.in_values is not None:
                in_values_claimed.update(entry.in_values)

        split_dir = competencia_data_dir / _SPLIT_DIRNAME / inms_key
        claimed_overall: set[str] = set()

        for categoria_key, entry in entries:
            if entry.in_values is not None:
                effective_values = set(entry.in_values)
            else:
                assert entry.catch_all_contains is not None
                effective_values = {
                    v for v in real_values if entry.catch_all_contains in v
                } - in_values_claimed
            claimed_overall |= effective_values

            filtered_rows = [
                row for row in rows if row[_GRUPO_EXECUTOR_COLUMN] in effective_values
            ]
            csv_path = split_dir / f"{categoria_key}.csv"
            try:
                _write_filtered_csv(csv_path, fieldnames, filtered_rows, delimiter)
            except OSError as exc:
                logger.error(f"falha ao escrever {csv_path}: {exc}")
                any_error = True
                continue

            csv_relpath = f"{_SPLIT_DIRNAME}/{inms_key}/{categoria_key}.csv"
            derived_config = _derive_config(base_config, categoria_key, csv_relpath, delimiter)
            config_path = config_dir / f"{base_stem}.{categoria_key}.yaml"
            try:
                _write_derived_config(config_path, derived_config)
            except OSError as exc:
                logger.error(f"falha ao escrever {config_path}: {exc}")
                any_error = True
                continue

            outcomes.append(SplitCategoriaOutcome(
                inms=inms_key, categoria=categoria_key, csv_path=csv_path,
                config_path=config_path, row_count=len(filtered_rows),
            ))

        outros_values = real_values - claimed_overall
        outros_rows = [row for row in rows if row[_GRUPO_EXECUTOR_COLUMN] in outros_values]
        outros_path = split_dir / f"{_OUTROS_NAME}.csv"
        try:
            _write_filtered_csv(outros_path, fieldnames, outros_rows, delimiter)
        except OSError as exc:
            logger.error(f"falha ao escrever {outros_path}: {exc}")
            any_error = True
            continue

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
