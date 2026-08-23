"""Resolução de entradas de `pyauditor measure` (ticket 06 SRP).

Separação das etapas de entrada que viviam no corpo de `run_measure`:
validação da competência, resolução do diretório de dados, descoberta de
configs, garantia do diretório de saída, leitura de `equipe.csv`/
responsáveis e carregamento/expansão de `categorias.yaml` (incl. stems de
configs derivadas — ADR 0002). O resultado é passado como dados puros para o
loop de medição (`run_measure`/`_runner`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from pyauditor.categoria_filter import base_config_stem
from pyauditor.cli.results import DIR_FAILURE_HINT, validate_competencia
from pyauditor.config.categorias import GrupoExecutorMode, load_categorias
from pyauditor.config.manifest import DatasetManifest
from pyauditor.config.models import IndicatorConfig
from pyauditor.engine.pipeline import discover_config_files
from pyauditor.excel.equipe import RESPONSAVEL_LABELS, read_responsaveis
from pyauditor.logging import logger

__all__: Final[tuple[str, ...]] = (
    'MeasureInputs',
    '_inms_key_from_contractual_id',
    'resolve_measure_inputs',
)


def _inms_key_from_contractual_id(contractual_id: str) -> str | None:
    """`INMS 1.1` -> `1.1` — chave usada em `categorias.yaml`."""
    parts = contractual_id.strip().split()
    if not parts:
        return None
    last = parts[-1]
    # Valida formato 1.N
    if '.' not in last:
        return None
    return last


@dataclass(frozen=True)
class MeasureInputs:
    """Entradas validadas e resolvidas de uma execução de `measure`."""

    orgao: str
    competencia_data_dir: Path
    configs: list[tuple[Path, str, IndicatorConfig]]
    target_dir: Path
    capa_fields: dict[str, object]
    warnings: list[str] = field(default_factory=list)
    per_inms: dict[str, list[tuple[str, GrupoExecutorMode]]] = field(
        default_factory=dict
    )
    derived_config_stems: set[str] = field(default_factory=set)
    categorias_file: object | None = None


def _load_responsaveis(
    equipe_path: Path | None,
    warnings: list[str],
) -> dict[str, object]:
    """Responsáveis do ROM vêm exclusivamente de `equipe.csv` (spec §6) —
    ausente/malformado é warning + '[a preencher]', nunca falha técnica."""
    capa_fields: dict[str, object] = {}
    if equipe_path is None:
        return capa_fields

    campos_equipe, avisos_equipe = read_responsaveis(equipe_path)
    capa_fields.update(campos_equipe)
    for warning in avisos_equipe:
        logger.warning(warning)
        warnings.append(warning)
    empty_fields = [f for f in RESPONSAVEL_LABELS if not capa_fields.get(f)]
    if empty_fields:
        warning = ''.join(
            [
                f'{equipe_path}: sem preencher: ',
                f'{", ".join(empty_fields)} — ROM mostra ',
                "'[a preencher]' nesses campos",
            ]
        )
        logger.warning(warning)
        warnings.append(warning)
    return capa_fields


def _load_categorias(
    config_dir: Path,
    expected_orgao: str | None,
    warnings: list[str],
) -> tuple[object | None, dict[str, list[tuple[str, GrupoExecutorMode]]]]:
    """Single-source categorias: carrega uma vez por execução (fallback para
    parent/<orgao>/categorias.yaml quando config_dir é _shared)."""
    categorias_file = None
    per_inms: dict[str, list[tuple[str, GrupoExecutorMode]]] = {}
    if expected_orgao is None:
        return categorias_file, per_inms

    categorias_path = config_dir / 'categorias.yaml'
    if not categorias_path.exists() and config_dir.name == '_shared':
        fallback = config_dir.parent / expected_orgao / 'categorias.yaml'
        if fallback.exists():
            categorias_path = fallback
    if not categorias_path.exists():
        return categorias_file, per_inms

    try:
        categorias_file = load_categorias(categorias_path)
        for cat_key, cat in categorias_file.categorias.items():
            for cat_inms_key, entry in cat.inms.items():
                if isinstance(entry, GrupoExecutorMode):
                    per_inms.setdefault(cat_inms_key, []).append(
                        (cat_key, entry)
                    )
        logger.debug('categorias carregadas de %s', categorias_path)
    except (OSError, ValueError) as exc:
        logger.warning(
            'falha ao carregar categorias %s: %s',
            categorias_path,
            exc,
        )
    return categorias_file, per_inms


def _derived_config_stems(
    per_inms: dict[str, list[tuple[str, GrupoExecutorMode]]],
) -> set[str]:
    """ADR 0002 (compat retroativa): configs por categoria que o `split`
    materializa em disco são descartadas silenciosamente da descoberta — o
    caminho de fato usado hoje é a expansão em memória."""
    derived_config_stems: set[str] = set()
    for categoria_inms_key, categoria_entries in per_inms.items():
        try:
            stem = base_config_stem(categoria_inms_key)
        except ValueError:
            continue
        derived_config_stems.update(
            f'{stem}.{cat_key}' for cat_key, _entry in categoria_entries
        )
    return derived_config_stems


def resolve_measure_inputs(
    competencia: str,
    config_dir: Path,
    data_dir: Path,
    output_dir: Path,
    *,
    expected_orgao: str | None = None,
    equipe_path: Path | None = None,
    manifest: DatasetManifest | None = None,
) -> tuple[MeasureInputs | None, str | None]:
    """Valida e resolve todas as entradas de `measure`.

    Returns:
        ``(inputs, None)`` em sucesso ou ``(None, mensagem_de_erro)`` quando
        uma etapa de entrada falha (competência inválida, configs ausentes,
        diretório de saída sem permissão). Warnings de equipe/categorias vão
        para dentro de ``inputs.warnings``.
    """
    orgao = expected_orgao or ''

    competencia_error = validate_competencia(competencia)
    if competencia_error is not None:
        return None, competencia_error

    year, month = competencia.split('-')
    competencia_data_dir = data_dir / year / month

    try:
        configs = discover_config_files(
            config_dir, expected_orgao=expected_orgao
        )
    except (OSError, ValueError) as exc:
        return None, f'falha ao carregar configs de {config_dir}: {exc}'
    if not configs:
        return None, f'nenhum config encontrado em {config_dir}'

    target_dir = output_dir / competencia
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        message = f'falha ao criar diretório {target_dir}: {exc}'
        return None, f'{message} — {DIR_FAILURE_HINT}'

    warnings: list[str] = []
    capa_fields = _load_responsaveis(equipe_path, warnings)
    categorias_file, per_inms = _load_categorias(
        config_dir, expected_orgao, warnings
    )
    derived_config_stems = _derived_config_stems(per_inms)

    inputs = MeasureInputs(
        orgao=orgao,
        competencia_data_dir=competencia_data_dir,
        configs=configs,
        target_dir=target_dir,
        capa_fields=capa_fields,
        warnings=warnings,
        per_inms=per_inms,
        derived_config_stems=derived_config_stems,
        categorias_file=categorias_file,
    )
    return inputs, None
