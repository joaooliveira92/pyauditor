"""Descoberta e carga de configs de indicador (YAML → `IndicatorConfig`).

Extraído de `engine/pipeline.py` (ticket 03 SRP): `load_config`,
`discover_config_files`/`discover_configs` e a injeção de órgão para
`configs/_shared/` (single-source). `pipeline.py` re-exporta os símbolos —
nenhum consumidor muda de import.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from pyauditor.config.models import IndicatorConfig

__all__ = (
    "discover_config_files",
    "discover_configs",
    "load_config",
)

_ORGAO_CONTRACT: dict[str, str] = {
    "MinC": "40/2022 - Ministério da Cultura",
    "MTur": "40/2022 - Ministério do Turismo",
}


def load_config(config_path: Path) -> IndicatorConfig:
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "indicator" not in raw:
        # Detect typo like `indicador:` — instead of silently skipping later
        for key in raw:
            if isinstance(key, str) and key.strip().lower() in (
                "indicador",
                "indicators",
                "indicatior",
            ):
                raise ValueError(
                    f"{config_path}: chave {key!r} encontrada, esperado 'indicator:' — "
                    "typo no YAML, corrija a chave"
                )
        # also check if file looks like an indicator config (inms-*.yaml) but missing key
        if config_path.name.startswith("inms-"):
            raise ValueError(
                f"{config_path}: chave 'indicator:' ausente — "
                "arquivo não é config válida de indicador"
            )
    return IndicatorConfig.model_validate(raw)


def _inject_orgao(config: IndicatorConfig, expected_orgao: str) -> IndicatorConfig:
    """Injeta `scope.orgao`/`contract` quando o YAML vem de `configs/_shared/`."""
    desired_contract = _ORGAO_CONTRACT.get(expected_orgao, config.scope.contract)
    if config.scope.orgao == expected_orgao and config.scope.contract == desired_contract:
        return config
    from pyauditor.config.models import Scope

    # `expected_orgao` é str livre no contrato, mas na prática só recebe
    # "MinC"/"MTur" (nível de fronteira) — Scope.orgao é
    # `Literal["MinC","MTur"]`; o range é validado por quem chama
    # _inject_orgao.
    new_scope = Scope(contract=desired_contract, orgao=expected_orgao)  # type: ignore[arg-type]
    return config.model_copy(update={"scope": new_scope})


def discover_config_files(
    config_dir: Path, expected_orgao: str | None = None
) -> list[tuple[Path, str, IndicatorConfig]]:
    """Same discovery as `discover_configs`, but keeps each config's source
    path and content hash alongside it — `measure()`'s provenance needs both,
    computed here (while `raw_text` is in hand) rather than re-reading the
    file a second time. `discover_configs` can't gain these without breaking
    its existing `list[IndicatorConfig]` callers.

    Quando `expected_orgao` é informado e o arquivo vem de `configs/_shared/`
    (single-source), o `scope` é injetado em runtime em vez de validar
    mismatch — o YAML canônico não carrega `scope` por órgão.
    """
    triples: list[tuple[Path, str, IndicatorConfig]] = []
    is_shared = config_dir.name == "_shared" or (config_dir / "_shared").exists()
    for path in sorted(config_dir.glob("*.yaml")):
        raw_text = path.read_text(encoding="utf-8")
        raw = yaml.safe_load(raw_text)
        if not isinstance(raw, dict) or "indicator" not in raw:
            # Detect typo in indicator key before silently skipping
            if isinstance(raw, dict):
                for key in raw:
                    if isinstance(key, str) and key.strip().lower() in (
                        "indicador",
                        "indicators",
                        "indicatior",
                        "indicator ",
                    ):
                        raise ValueError(
                            f"{path}: chave {key!r} encontrada, esperado 'indicator:' — "
                            "typo no YAML"
                        )
                if path.name.startswith("inms-"):
                    raise ValueError(
                        f"{path}: chave 'indicator:' ausente — "
                        "arquivo não é config válida de indicador"
                    )
            # Not an indicator config (e.g. `datasets.yaml`, the manifest that
            # now lives alongside the indicators) — skip it.
            continue
        config = IndicatorConfig.model_validate(raw)
        if expected_orgao is not None:
            # Single-source: injetar órgão/contrato em vez de falhar.
            if is_shared or config_dir.name == "_shared":
                config = _inject_orgao(config, expected_orgao)
            elif config.scope.orgao != expected_orgao:
                raise ValueError(
                    f"{path}: scope.orgao={config.scope.orgao!r} não corresponde ao "
                    f"órgão solicitado {expected_orgao!r} — config no diretório errado"
                )
        content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        triples.append((path, content_hash, config))
    return triples


def discover_configs(config_dir: Path, expected_orgao: str | None = None) -> list[IndicatorConfig]:
    """Load every indicator config from *config_dir* (one per `*.yaml`,
    skipping non-indicator manifests like `datasets.yaml`).

    When *expected_orgao* is given, every config whose ``scope.orgao`` differs
    is a hard error (per-conf layout is per-órgão: `configs/<órgão>/`).
    """
    return [config for _, _, config in discover_config_files(config_dir, expected_orgao)]