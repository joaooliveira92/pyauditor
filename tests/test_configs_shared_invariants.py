"""Invariantes compartilhados entre órgãos.

`calculation`/`target`/`penalty`/`quality_gates`/`source` devem ser
idênticos entre MinC e MTur para cada indicador base. Drift contratual
(ex.: meta 98.0 vs 97.0) deve falhar explicitamente. `scope` e
`acceptance_test` são allowlist de divergência esperada.

Ticket 01 — Higienização e prefatoração.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent
MINC_DIR = REPO_ROOT / 'configs' / 'MinC'
MTUR_DIR = REPO_ROOT / 'configs' / 'MTur'

# Campos que DEVEM ser idênticos entre órgãos. `source` é contrato de dataset
# (mesmo CSV lógico),
# `quality_gates`/`calculation`/`target`/`penalty` são regra do Anexo D.
INVARIANT_TOP_LEVEL_KEYS = (
    'source',
    'quality_gates',
    'calculation',
    'target',
    'penalty',
)

# `scope` e `acceptance_test` divergem por design (órgão/contrato e snapshot da
# competência).
ALLOWLIST_DIVERGENT_KEYS = {'scope', 'acceptance_test', 'indicator'}


def _load_raw_yaml(path: Path) -> dict[str, object]:
    text = path.read_text(encoding='utf-8')
    raw: object = yaml.safe_load(text)
    assert isinstance(raw, dict), f'{path}: YAML raiz deve ser mapping'
    assert isinstance(raw, dict)
    return raw


def _base_config_stems() -> list[str]:
    """Stems `inms-NN` que existem como base em ambos os órgãos (sem
    categoria)."""
    minc_bases = {p.name for p in MINC_DIR.glob('inms-[0-9]*.yaml')}
    mtur_bases = {p.name for p in MTUR_DIR.glob('inms-[0-9]*.yaml')}

    # Filtra só os que são base (sem ponto extra): inms-01.yaml ok,
    # inms-01.ATENDIMENTO_N1.yaml não
    def is_base(name: str) -> bool:
        stem = name.removesuffix('.yaml')
        # base tem exatamente um hífen e dois dígitos: inms-01
        return stem.count('.') == 0

    common = sorted({n for n in minc_bases & mtur_bases if is_base(n)})
    return common


def test_shared_invariants_between_orgaos() -> None:
    stems = _base_config_stems()
    # Pós-migração single-source (ticket 02): bases per-órgão foram
    # removidas e substituídas por configs/_shared. Nesse caso o
    # invariante é verificado via discovery injetado.
    if len(stems) < 14:
        # Verifica single-source: _shared deve ter 14 bases e injeção
        # MinC/MTur deve produzir mesmo calculation/target/penalty.
        from pyauditor.engine.pipeline import discover_configs

        shared_dir = REPO_ROOT / 'configs' / '_shared'
        assert shared_dir.is_dir(), 'configs/_shared deve existir pós-migração'
        minc_configs = {
            c.indicator.id: c
            for c in discover_configs(shared_dir, expected_orgao='MinC')
        }
        mtur_configs = {
            c.indicator.id: c
            for c in discover_configs(shared_dir, expected_orgao='MTur')
        }
        assert len(minc_configs) >= 14
        failures_ss: list[str] = []
        for iid, mc in minc_configs.items():
            mtc = mtur_configs.get(iid)
            assert mtc is not None, f'{iid} ausente em MTur via _shared'
            if mc.calculation != mtc.calculation:
                failures_ss.append(f'{iid}: calculation diverge')
            if mc.target != mtc.target:
                failures_ss.append(f'{iid}: target diverge')
            if mc.penalty != mtc.penalty:
                failures_ss.append(f'{iid}: penalty diverge')
            if mc.quality_gates != mtc.quality_gates:
                failures_ss.append(f'{iid}: quality_gates diverge')
            if mc.source != mtc.source:
                failures_ss.append(f'{iid}: source diverge')
        assert not failures_ss, (
            'Invariantes via _shared divergiram:\n' + '\n'.join(failures_ss)
        )
        return

    failures: list[str] = []
    for fname in stems:
        minc_raw = _load_raw_yaml(MINC_DIR / fname)
        mtur_raw = _load_raw_yaml(MTUR_DIR / fname)

        for key in INVARIANT_TOP_LEVEL_KEYS:
            minc_val = minc_raw.get(key)
            mtur_val = mtur_raw.get(key)
            if minc_val != mtur_val:
                failures.append(
                    f'{fname}: chave {key!r} diverge entre MinC e MTur\n'
                    f'  MinC: {minc_val!r}\n'
                    f'  MTur: {mtur_val!r}'
                )

        # `indicator.name` e `contractual_id` também são invariantes (mesmo
        # indicador)
        for subkey in ('contractual_id', 'name'):
            minc_ind = minc_raw.get('indicator')
            mtur_ind = mtur_raw.get('indicator')
            assert isinstance(minc_ind, dict)
            assert isinstance(mtur_ind, dict)
            if minc_ind.get(subkey) != mtur_ind.get(subkey):
                failures.append(
                    f'{fname}: indicator.{subkey} diverge — '
                    f'MinC={minc_ind.get(subkey)!r} '
                    f'MTur={mtur_ind.get(subkey)!r}'
                )

    assert not failures, 'Invariantes compartilhados divergiram:\n' + '\n'.join(
        failures
    )


def test_datasets_yaml_is_identical() -> None:
    minc_ds = (MINC_DIR / 'datasets.yaml').read_text(encoding='utf-8')
    mtur_ds = (MTUR_DIR / 'datasets.yaml').read_text(encoding='utf-8')
    msg = 'datasets.yaml deve ser idêntico entre órgãos (cópia byte-a-byte)'
    assert minc_ds == mtur_ds, msg


def test_no_tracked_derived_configs() -> None:
    """Garante que derivados `inms-*.*.yaml` não estão trackeados
    (gitignored)."""
    import subprocess

    result = subprocess.run(
        [
            'git',
            'ls-files',
            '--cached',
            'configs/MinC/inms-*.*.yaml',
            'configs/MTur/inms-*.*.yaml',
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    tracked = [line for line in result.stdout.splitlines() if line.strip()]
    assert not tracked, (
        f'Derivados trackeados encontrados (deveriam ser gitignored): {tracked}'
    )


def test_derived_configs_are_gitignored() -> None:
    import subprocess

    # Um derivado sintético deve ser ignorado pelo gitignore atual
    result = subprocess.run(
        [
            'git',
            'check-ignore',
            '-v',
            'configs/MinC/inms-01.ATENDIMENTO_N1.yaml',
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        'gitignore deveria cobrir configs/*/inms-*.*.yaml'
    )
    assert 'configs/*/inms-*.*.yaml' in result.stdout
