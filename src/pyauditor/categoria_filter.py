"""Helpers compartilhados de filtragem Categoria/`Grupo_executor` (spec
§14.1-§14.3): resolve as entradas `in_values`/`catch_all_contains` de
`categorias.yaml` contra os literais reais de `Grupo_executor` do CSV bruto,
incluindo o resto `outros`. `cli/split.py` (grava os CSVs filtrados) e
`excel/sintetico.py` (o relatório sintetico.xlsx, só leitura, sobre as
mesmas regras — ticket 05) precisam do mesmo cálculo de `outros` — este é o
único lugar que mantém os dois comportamentos idênticos.

Vive fora de `cli/` para que `excel/` (que nunca depende de `cli/`) também
possa importar.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Final

from pyauditor.config.categorias import GrupoExecutorMode

__all__: Final[tuple[str, ...]] = (
    "GRUPO_EXECUTOR_COLUMN",
    "base_config_stem",
    "compute_categoria_values",
    "outros_warning",
    "read_raw_csv",
    "unmatched_in_values_warnings",
)

GRUPO_EXECUTOR_COLUMN: Final[str] = "Grupo_executor"
_INMS_KEY_RE: Final = re.compile(r"^1\.(\d+)$")


def base_config_stem(inms_key: str) -> str:
    """`"1.7"` -> `"inms-07"` — mesma convenção dos configs base
    `inms-NN.yaml` já descobertos por `measure`."""
    match = _INMS_KEY_RE.match(inms_key)
    if match is None:
        raise ValueError(
            f"chave INMS inesperada em categorias.yaml: {inms_key!r} (esperado '1.<n>')"
        )
    return f"inms-{int(match.group(1)):02d}"


_GRUPO_EXECUTOR_ALIAS: Final[str] = GRUPO_EXECUTOR_COLUMN.replace("_", " ")


def _normalize_grupo_executor_header(fieldnames: list[str]) -> list[str]:
    """Alguns exports usam `"Grupo executor"` (espaço) em vez do `"Grupo_executor"`
    (underscore) que todo o resto do pipeline convenciona — confirmado em produção
    (INMS 1.7, 2026-06: MinC e MTur exportam com espaço, diferente de 1.1-1.3).
    Normaliza para o nome canônico na leitura, uma vez, para que nenhum chamador
    precise conhecer as duas variantes."""
    if GRUPO_EXECUTOR_COLUMN in fieldnames or _GRUPO_EXECUTOR_ALIAS not in fieldnames:
        return fieldnames
    return [GRUPO_EXECUTOR_COLUMN if name == _GRUPO_EXECUTOR_ALIAS else name for name in fieldnames]


def read_raw_csv(
    path: Path, delimiter: str, encoding: str
) -> tuple[list[str], list[dict[str, str]]]:
    """Como `engine.pipeline.load_rows`, mas também devolve os nomes de
    coluna — os chamadores precisam deles pra gravar `outros.csv` com
    cabeçalho mesmo quando o CSV bruto não tem nenhuma linha, e pra checar
    quais colunas opcionais (`No prazo`, `DataHoraSolicitacao`/
    `DataHoraFim`) estão de fato presentes."""
    with path.open(encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: CSV vazio ou sem linha de cabeçalho")
        raw_fieldnames = [name.strip() for name in reader.fieldnames]
        fieldnames = _normalize_grupo_executor_header(raw_fieldnames)
        rename = dict(zip(raw_fieldnames, fieldnames, strict=True))
        reader.fieldnames = raw_fieldnames
        rows = [
            {rename[name]: (row.get(name) or "").strip() for name in raw_fieldnames}
            for row in reader
        ]
    return fieldnames, rows


def compute_categoria_values(
    entries: list[tuple[str, GrupoExecutorMode]], real_values: set[str]
) -> tuple[dict[str, set[str]], set[str]]:
    """Resolve o conjunto efetivo de literais `Grupo_executor` de cada
    categoria contra *real_values*, mais o resto `outros` (spec
    §14.1/§14.3): `catch_all_contains` exclui o que `in_values` já
    reivindicou dentro do mesmo INMS. Devolve `(per_categoria,
    outros_values)`, `per_categoria` na ordem de *entries*.

    Valida que nenhuma linha pertence a mais de uma categoria — sobreposição
    entre ``in_values`` de categorias distintas é erro (issue 01).
    """
    # Validação de sobreposição entre in_values explícitos
    seen_in_values: dict[str, str] = {}
    for categoria_key, entry in entries:
        if entry.in_values is not None:
            for val in entry.in_values:
                if val in seen_in_values:
                    raise ValueError(
                        f"Grupo_executor {val!r} aparece em mais de uma categoria "
                        f"({seen_in_values[val]!r} e {categoria_key!r}) — categorias "
                        "devem ser disjuntas, nenhuma linha pode ser contada duas vezes"
                    )
                seen_in_values[val] = categoria_key

    in_values_claimed: set[str] = set()
    for _categoria_key, entry in entries:
        if entry.in_values is not None:
            in_values_claimed.update(entry.in_values)

    claimed_overall: set[str] = set()
    per_categoria: dict[str, set[str]] = {}
    for categoria_key, entry in entries:
        if entry.in_values is not None:
            effective_values = set(entry.in_values)
        else:
            assert entry.catch_all_contains is not None
            effective_values = {
                v for v in real_values if entry.catch_all_contains in v
            } - in_values_claimed
        # Validação pós-resolução: effective_values não pode intersectar já reivindicado
        overlap = effective_values & claimed_overall
        if overlap:
            raise ValueError(
                f"categoria {categoria_key!r} sobrepõe valores já reivindicados "
                f"{sorted(overlap)!r} — nenhuma linha pode pertencer a duas categorias"
            )
        claimed_overall |= effective_values
        per_categoria[categoria_key] = effective_values

    outros_values = real_values - claimed_overall
    return per_categoria, outros_values


def unmatched_in_values_warnings(
    *,
    inms_key: str,
    orgao: str,
    competencia: str,
    entries: list[tuple[str, GrupoExecutorMode]],
    real_values: set[str],
    raw_csv_path: Path,
) -> list[str]:
    """Cross-check (issue 09): `in_values` de *entries* contra os literais
    reais de `Grupo_executor` do CSV bruto. Um typo/renomeação no export gera
    categoria sem linhas — indistinguível de zero atividade, por isso o aviso.

    Devolve as mensagens prontas (strings verbatim — as mesmas que
    `cli/measure.py` e `cli/split.py` emitiam cada um no seu bloco), para o
    chamador logar e acumular. Sem efeito colateral de log aqui para o mesmo
    texto servir aos dois consumidores.
    """
    warnings: list[str] = []
    for cat_key, entry in entries:
        if entry.in_values is None:
            continue
        unmatched = [v for v in entry.in_values if v not in real_values]
        if not unmatched:
            continue
        prefixo = f"INMS {inms_key} ({orgao}/{competencia}), categoria {cat_key}: "
        if not (set(entry.in_values) & real_values):
            warnings.append(
                f"{prefixo}in_values {unmatched!r} sem correspondência em "
                f"Grupo_executor do CSV ({raw_csv_path}) — possível "
                "typo/renomeação, categoria ficará sem linhas"
            )
        elif unmatched:
            warnings.append(
                f"{prefixo}in_values {unmatched!r} sem correspondência — "
                "valores não encontrados no CSV"
            )
    return warnings


def outros_warning(
    *,
    inms_key: str,
    orgao: str,
    competencia: str,
    outros_count: int,
) -> str:
    """Warning monolótono de linhas `outros` (não classificadas em nenhuma
    categoria) — mesma mensagem emitida por `split` e `measure`."""
    return (
        f"INMS {inms_key} ({orgao}/{competencia}), categoria outros: "
        f"{outros_count} linha(s) não classificada(s) em nenhuma categoria — "
        "revisar categorias.yaml"
    )
