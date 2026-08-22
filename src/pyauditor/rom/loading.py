"""Leitura compartilhada dos artefatos de ROM (`report`/`consolidate`,
ticket 07): sumários de medição (`*.json` em `roms/<orgao>/<competência>`) e
o valor contratual mensal (`objetos.csv`). Fonte única — antes duplicada,
verbatim, em `cli/report.py` e `cli/consolidate.py`.
"""

import json
from pathlib import Path

from pyauditor.excel.objetos import OBJETOS_FILENAME, read_objetos
from pyauditor.rom.summary import IndicatorSummary

_ORGAOS: tuple[str, ...] = ("MinC", "MTur")


def load_summaries(roms_dir: Path) -> list[IndicatorSummary]:
    """Carrega os sumários (`*.json`) de `roms_dir`, cross-checando o `orgao`
    do sidecar contra o diretório de origem (`roms/<orgao>/<competência>` ou
    `roms/<orgao>`). `ValueError` em sumário inválido/mal-rotulado propaga —
    é falha técnica, não dado ausente."""
    expected_orgao = roms_dir.parent.name if roms_dir.parent.name in _ORGAOS else None
    if expected_orgao is None and roms_dir.name in _ORGAOS:
        expected_orgao = roms_dir.name
    summaries: list[IndicatorSummary] = []
    for summary_path in sorted(roms_dir.glob("*.json")):
        try:
            raw = json.loads(summary_path.read_text(encoding="utf-8"))
            summary = IndicatorSummary(**raw)
            if expected_orgao is not None and summary.orgao != expected_orgao:
                raise ValueError(
                    f"{summary_path}: orgao {summary.orgao!r} no sidecar diverge do diretório "
                    f"de origem {expected_orgao!r} — sidecar mal-rotulado/copiado"
                )
            summaries.append(summary)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ValueError(f"sumário inválido em {summary_path}: {exc}") from exc
    return summaries


def read_valor_base(data_dir: Path, warnings: list[str]) -> tuple[float | None, tuple[float, ...]]:
    """`objetos.csv` → `(valor_base, itens)`. Ausente → `(None, ())` com
    warning (glosa não calculada); malformado → `ValueError` (falha técnica)."""
    path = data_dir / OBJETOS_FILENAME
    try:
        objetos = read_objetos(path)
    except FileNotFoundError:
        warnings.append(f"objetos.csv não encontrado em {data_dir} — glosa não calculada")
        return None, ()
    except ValueError as exc:
        raise ValueError(f"objetos.csv malformado em {path}: {exc}") from exc
    warnings.extend(objetos.warnings)
    return objetos.total_mensal, objetos.itens
