"""ROMs combinados 'both' de `pyauditor measure` (ticket 07 SRP).

`write_combined_roms` (que vivia em `cli/measure.py`) escreve, sob
`output_dir/both/<competencia>/`, um markdown por indicador com os ROMs de
ambos os órgãos empilhados. `cli/measure.py` reexporta a função mantendo a
API pública (consumidores: `cli/main.py`).
"""

from __future__ import annotations

from pathlib import Path

from pyauditor.cli.measure_contracts import _MeasuredIndicator
from pyauditor.cli.results import WRITE_FAILURE_HINT
from pyauditor.logging import logger
from pyauditor.periodo import PeriodoAfericao
from pyauditor.rom.render import render_combined_rom

__all__: tuple[str, ...] = ('write_combined_roms',)


def write_combined_roms(
    per_orgao: dict[str, list[_MeasuredIndicator]],
    competencia: str,
    output_dir: Path,
    *,
    periodo: PeriodoAfericao | None = None,
) -> None:
    """Given the measured indicators of each orgão (from `run_measure(...,
    collect=...)` calls with `--orgao both`), write under
    `output_dir/both/<competencia>/` one markdown per indicator with both
    orgãos' ROMs stacked. Skips indicators that only measured in one orgão
    (warning, no combined render without the pair)."""
    both_dir = output_dir / 'both' / competencia
    both_dir.mkdir(parents=True, exist_ok=True)

    by_id: dict[str, dict[str, _MeasuredIndicator]] = {}
    for orgao, measured in per_orgao.items():
        for item in measured:
            by_id.setdefault(item.indicator_id, {})[orgao] = item

    for indicator_id, orgs in sorted(by_id.items()):
        if len(orgs) < 2:
            missing = ', '.join(sorted({'MinC', 'MTur'} - set(orgs)))
            logger.warning(
                "ROM combinado 'both' não gerado para %s: falta medição de %s",
                indicator_id,
                missing,
            )
            continue

        minc = orgs['MinC']
        mtur = orgs['MTur']
        capa_by_orgao = {
            'MinC': minc.capa_fields,
            'MTur': mtur.capa_fields,
        }
        combined_path = both_dir / f'{minc.safe_id}.md'
        try:
            _ = combined_path.write_text(
                render_combined_rom(
                    minc.result,
                    mtur.result,
                    capa_by_orgao,
                    competencia=competencia,
                    periodo=periodo,
                ),
                encoding='utf-8',
            )
        except OSError as exc:
            logger.error(
                'falha ao escrever %s: %s — %s',
                combined_path,
                exc,
                WRITE_FAILURE_HINT,
            )
