"""`pyauditor measure <competência>` — run every configured indicator, write one
ROM Markdown per indicator, report hard failures (spec §4/§6).

Alongside each `<indicator.id>.md` ROM, also writes a `<indicator.id>.json`
structured summary (see `rom/summary.py`) — `report` (ticket 09) reads these
JSON sidecars rather than re-parsing the ROM's prose Markdown.

Datasets are organized per competência: `measure 2026-06 --data-dir input`
reads every CSV from `input/2026/06/` (derived from the competência, never
from the data-dir root). Keeping each competência in its own folder lets one
project hold the data of every past aferição side by side.

Spec competencia-cli-equipe: os ROMs recebem Competência/Período do argumento
da CLI (`periodo`) e os Responsáveis de `equipe.csv` (`equipe_path`) — nada
vem mais da capa. Com `periodo`, tanto o caminho single (whole_indicator) via
`engine.measure()` quanto o caminho derivado (categorias em memória) filtram
pela janela da competência através do backbone `measurement_source()`
(ticket 05) — `suppress_duplicate_split_warnings` evita emitir o mesmo
aviso duas vezes quando `run` já rodou `split` na mesma passada.

Ticket 07 SRP: a resolução de entradas vive em `cli/measure_inputs.py`, o
loop de medição em `cli/measure_run.py`, os ROMs combinados `both` em
`cli/measure_combined.py` e os contratos (dataclasses/helper de nome) em
`cli/measure_contracts.py`. Este módulo é o orquestrador e reexporta a API
pública.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from pyauditor.cli.measure_combined import write_combined_roms
from pyauditor.cli.measure_contracts import (
    IndicatorOutcome,
    _MeasuredIndicator,
)
from pyauditor.cli.measure_inputs import resolve_measure_inputs
from pyauditor.cli.measure_run import MeasureLoop
from pyauditor.cli.results import (
    DependencyCheck,
)
from pyauditor.commands import contracts
from pyauditor.config.manifest import DatasetManifest
from pyauditor.logging import log_event, logger
from pyauditor.periodo import PeriodoAfericao

__all__: Final[tuple[str, ...]] = (
    'IndicatorOutcome',
    'MeasureResult',
    '_MeasuredIndicator',
    'check_measure_ready',
    'run_measure',
    'write_combined_roms',
)

# `MeasureResult` vive no contrato neutro `pyauditor.commands.contracts`
# (ticket 11 SRP) — reexportado aqui para preservar a API pública.
MeasureResult = contracts.MeasureResult


def check_measure_ready(*_args: object, **_kwargs: object) -> DependencyCheck:
    """`measure` only needs configs+data, both external inputs it validates
    itself — no dependency on another Command's output."""
    return DependencyCheck(satisfied=True, missing=())


def run_measure(
    competencia: str,
    config_dir: Path,
    data_dir: Path,
    output_dir: Path,
    manifest: DatasetManifest | None = None,
    *,
    expected_orgao: str | None = None,
    equipe_path: Path | None = None,
    periodo: PeriodoAfericao | None = None,
    strict: bool = False,
    collect: list[_MeasuredIndicator] | None = None,
    suppress_duplicate_split_warnings: bool = False,
) -> MeasureResult:
    """*suppress_duplicate_split_warnings* (ticket 05): `True` quando `split`
    já rodou para esta competência/órgão na mesma passada de `run` (o
    orchestration sempre despacha `split` antes de `measure`) — o caminho
    categorial em memória então suprime o próprio WARN de janela vazia e o
    INFO de descarte, já que `split` os logou para o mesmo dataset bruto.
    `pyauditor measure` isolado (default `False`) recebe o WARN/INFO aqui —
    antes este caminho nunca os emitia, ao contrário do caminho single
    (whole_indicator) abaixo."""
    orgao = expected_orgao or ''

    def _error(message: str) -> MeasureResult:
        logger.error(message)
        return MeasureResult(
            status='error',
            competencia=competencia,
            orgao=orgao,
            indicators=(),
            warnings=(),
            error_message=message,
        )

    inputs, error = resolve_measure_inputs(
        competencia,
        config_dir,
        data_dir,
        output_dir,
        expected_orgao=expected_orgao,
        equipe_path=equipe_path,
        manifest=manifest,
    )
    if error is not None:
        return _error(error)
    if inputs is None:
        return _error('falha interna: entradas não resolvidas')

    loop = MeasureLoop(
        orgao=orgao,
        competencia=competencia,
        competencia_data_dir=inputs.competencia_data_dir,
        target_dir=inputs.target_dir,
        per_inms=inputs.per_inms,
        derived_config_stems=inputs.derived_config_stems,
        categorias_file=inputs.categorias_file,
        manifest=manifest,
        periodo=periodo,
        strict=strict,
        suppress_duplicate_split_warnings=suppress_duplicate_split_warnings,
        capa_fields=inputs.capa_fields,
    )
    result = loop.run_configs(inputs.configs, collect=collect)

    warnings = inputs.warnings + result.warnings
    any_hard_failure = result.any_hard_failure
    outcomes = result.outcomes

    # Resumo conciso por órgão (INFO) — no lugar das N linhas repetidas.
    total = len(outcomes)
    ok = sum(1 for o in outcomes if not o.hard_failure)
    log_event(
        'measure_done',
        f'{orgao or "órgão"}: {ok}/{total} indicador(es) apurado(s)',
        'INFO',
        orgao=orgao,
        competencia=competencia,
        status='error' if any_hard_failure else 'done',
    )

    error_message = (
        'um ou mais indicadores tiveram falha de medição'
        if any_hard_failure
        else None
    )
    return MeasureResult(
        status='error' if any_hard_failure else 'done',
        competencia=competencia,
        orgao=orgao,
        indicators=tuple(outcomes),
        warnings=tuple(warnings),
        error_message=error_message,
    )
