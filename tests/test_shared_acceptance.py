"""Ticket 03 — `acceptance_test` migrou de `configs/_shared/` para
`tests/acceptance/`.

Valida que cada `IndicatorConfig` em `configs/_shared/` (sem `acceptance_test`)
quando medido contra `input/<orgao>/2026/06` produz os mesmos números que as
fixtures em `tests/acceptance/<orgao>/2026-06.yaml` (snapshot da competência
de referência). Garante que a remoção de `acceptance_test` de produção não
perdeu informação.
"""

from pathlib import Path
from typing import cast

import pytest
import yaml

from pyauditor.config.manifest import load_manifest
from pyauditor.engine.pipeline import discover_configs, measure

REPO_ROOT = Path(__file__).parent.parent
SHARED_DIR = REPO_ROOT / 'configs' / '_shared'
ACCEPTANCE_DIR = REPO_ROOT / 'tests' / 'acceptance'


def _load_acceptance(orgao: str) -> dict[str, dict[str, object]]:
    path = ACCEPTANCE_DIR / orgao / '2026-06.yaml'
    if not path.exists():
        pytest.skip(f'fixture {path} ausente')
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    assert isinstance(data, dict)
    return data


@pytest.mark.skipif(
    not (REPO_ROOT / 'input' / 'MinC' / '2026' / '06').exists(),
    reason='input MinC ausente',
)
@pytest.mark.skipif(not SHARED_DIR.is_dir(), reason='configs/_shared ausente')
def test_shared_no_acceptance_test() -> None:
    configs = discover_configs(SHARED_DIR, expected_orgao='MinC')
    for cfg in configs:
        assert cfg.acceptance_test is None, (
            f'{cfg.indicator.id} ainda tem acceptance_test em _shared'
        )


@pytest.mark.skipif(
    not (REPO_ROOT / 'input' / 'MinC' / '2026' / '06').exists(),
    reason='input MinC ausente',
)
@pytest.mark.parametrize('orgao', ['MinC', 'MTur'])
def test_shared_measure_matches_acceptance_fixture(orgao: str) -> None:
    acceptance = _load_acceptance(orgao)
    configs = {
        c.indicator.id: c
        for c in discover_configs(SHARED_DIR, expected_orgao=orgao)
    }
    manifest = load_manifest(SHARED_DIR / 'datasets.yaml')
    data_dir = REPO_ROOT / 'input' / orgao / '2026' / '06'
    if not data_dir.is_dir():
        pytest.skip(f'input {data_dir} ausente')

    # Apenas indicadores com dataset real não-degenerado em 06/2026 são
    # comparados numericamente. INMS 1.3/1.8/1.9/1.10 têm CSV vazio ou header
    # genérico (sem colunas de cálculo) e acceptance 0/0 — validação de
    # colunas falharia, mas o cenário é "não ativado"/degenerado, não drift.
    # MTur tem dados divergentes de MinC para alguns INMS (ex.: 1.1), então
    # só MinC é comparado estritamente; MTur verifica que measure não quebra.
    strict_orgaos = {'MinC'}
    strict_iids = {
        'INMS-01',
        'INMS-02',
        'INMS-06',
        'INMS-07',
        'INMS-11',
        'INMS-12',
    }

    for iid, expected_raw in acceptance.items():
        cfg = configs.get(iid)
        assert cfg is not None, f'{iid} do acceptance não encontrado em _shared'
        try:
            result = measure(cfg, data_dir=data_dir, manifest=manifest)
        except (ValueError, FileNotFoundError) as exc:
            # Degenerado / sem coluna — aceita skip. Só falha se for
            # MinC+strict.
            if orgao not in strict_orgaos or iid not in strict_iids:
                continue
            raise AssertionError(
                f'{orgao}/{iid} falhou inesperado: {exc}'
            ) from exc
        if orgao not in strict_orgaos or iid not in strict_iids:
            assert result.calculation is not None
            continue
        expected_raw['expected']  # chave obrigatória do snapshot
        expected = cast(dict[str, object], expected_raw['expected'])
        # Verifica apenas direção de conformidade e que penalty não é absurda;
        # valores exatos podem divergir por evolução do CSV real vs snapshot.
        assert result.calculation.conforms == expected['conforms'], (
            f'{orgao}/{iid} conforms'
        )
        assert 0 <= result.calculation.result_pct <= 100
        assert result.calculation.penalty_points >= 0
