"""Compartilha a filtragem por categoria e ``Grupo_executor``.

Resolve as entradas ``in_values`` e ``catch_all_contains`` de
``categorias.yaml`` contra os valores reais de ``Grupo_executor`` do CSV
bruto, incluindo a categoria residual ``outros`` (especificação
§14.1-§14.3).

O módulo fica fora de ``cli`` para que ``cli/split.py`` e
``excel/sintetico.py`` usem o mesmo cálculo sem criar dependência de ``excel``
para ``cli``.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pyauditor.config.categorias import GrupoExecutorMode

__all__: Final[tuple[str, ...]] = (
    'GRUPO_EXECUTOR_COLUMN',
    'RawCsv',
    'Warning',
    'WarningTarget',
    'base_config_stem',
    'compute_categoria_values',
    'outros_warning',
    'read_raw_csv',
    'unmatched_in_values_warnings',
)


@dataclass(frozen=True)
class WarningTarget:
    """Campo exato de configuração que causou um `Warning`.

    ``path`` segue a mesma convenção de array-de-chaves já usada pelo form
    engine genérico do `app.js` (ex.: ``("config", "categorias",
    "ATENDIMENTO_N1", "inms", "1.1", "in_values")``), pra que a UI só
    precise navegar até ele sem reconhecer o `code` do warning.
    """

    family: str
    orgao: str
    path: tuple[str, ...]


@dataclass(frozen=True)
class Warning:
    """Aviso estruturado gerado durante a filtragem por categoria.

    ``message`` preserva o texto pronto para registro (mesmo conteúdo que
    hoje circula como ``str``); os demais campos dão contexto navegável sem
    exigir que o chamador reanalise a mensagem. ``code`` identifica o tipo de
    aviso de forma estável (``"unstructured"`` para o texto livre dos demais
    pontos do pipeline que ainda não foram migrados). ``target`` aponta pro
    campo exato de configuração que causou o aviso, quando existir um — nem
    todo `code` tem um alvo editável (ex.: a categoria residual "outros").
    """

    code: str
    message: str
    orgao: str | None
    competencia: str | None
    inms_key: str | None
    categoria: str | None
    target: WarningTarget | None = None

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True)
class RawCsv:
    """Resultado de uma leitura bruta: campos, filas e anomalias detectadas.

    ``ragged_rows`` conta as filas cujo número de campos excede o da cabecera
    (campo livre contendo o delimitador desloca as colunas). O ``DictReader``
    enfia esse excedente na chave ``None``; aqui ele é contado em vez de ser
    descartado em silêncio, porque num contexto de aferição uma fila truncada
    é dado que pode mudar o resultado sem deixar rastro.
    """

    fieldnames: list[str]
    rows: list[dict[str, str]]
    ragged_rows: int = 0


GRUPO_EXECUTOR_COLUMN: Final[str] = 'Grupo_executor'
_INMS_KEY_RE: Final[re.Pattern[str]] = re.compile(r'^1\.(\d+)$')
_GRUPO_EXECUTOR_ALIAS: Final[str] = GRUPO_EXECUTOR_COLUMN.replace('_', ' ')


def base_config_stem(inms_key: str) -> str:
    """Converte uma chave INMS no nome-base do arquivo de configuração.

    Args:
        inms_key: Chave contratual no formato ``1.<n>``.

    Returns:
        Nome-base no formato ``inms-NN``.

    Raises:
        ValueError: Se a chave não seguir o formato esperado.
    """
    match = _INMS_KEY_RE.fullmatch(inms_key)
    if match is None:
        raise ValueError(
            'chave INMS inesperada em categorias.yaml: '
            f"{inms_key!r} (esperado '1.<n>')"
        )
    return f'inms-{int(match.group(1)):02d}'


def _normalize_grupo_executor_header(fieldnames: list[str]) -> list[str]:
    """Normaliza a variante conhecida do cabeçalho ``Grupo_executor``."""
    if (
        GRUPO_EXECUTOR_COLUMN in fieldnames
        or _GRUPO_EXECUTOR_ALIAS not in fieldnames
    ):
        return fieldnames
    return [
        GRUPO_EXECUTOR_COLUMN if name == _GRUPO_EXECUTOR_ALIAS else name
        for name in fieldnames
    ]


def read_raw_csv(
    path: Path,
    delimiter: str,
    encoding: str,
) -> RawCsv:
    """Lê um CSV bruto e normaliza seus nomes de coluna.

    Args:
        path: Caminho do arquivo CSV.
        delimiter: Delimitador usado no arquivo.
        encoding: Codificação de caracteres do arquivo.

    Returns:
        Um :class:`RawCsv` com os nomes de coluna, as linhas normalizadas e o
        número de linhas com campos sobrantes (``ragged``).

    Raises:
        ValueError: Se o CSV estiver vazio ou não tiver cabeçalho.
        OSError: Se o arquivo não puder ser lido.
    """
    with path.open(encoding=encoding, newline='') as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if reader.fieldnames is None:
            raise ValueError(f'{path}: CSV vazio ou sem linha de cabeçalho')

        raw_fieldnames = [name.strip() for name in reader.fieldnames]
        fieldnames = _normalize_grupo_executor_header(raw_fieldnames)
        rename = dict(zip(raw_fieldnames, fieldnames, strict=True))
        reader.fieldnames = raw_fieldnames
        rows: list[dict[str, str]] = []
        ragged_rows = 0
        for row in reader:
            if row.get(None):
                # DictReader enfia os campos sobrantes (mais colunas que o
                # cabeçalho) na chave `None` — contados como anomalia.
                ragged_rows += 1
            rows.append(
                {
                    rename[name]: (row.get(name) or '').strip()
                    for name in raw_fieldnames
                }
            )
    return RawCsv(
        fieldnames=fieldnames,
        rows=rows,
        ragged_rows=ragged_rows,
    )


def compute_categoria_values(
    entries: list[tuple[str, GrupoExecutorMode]],
    real_values: set[str],
) -> tuple[dict[str, set[str]], set[str]]:
    """Resolve os valores de ``Grupo_executor`` de cada categoria.

    ``catch_all_contains`` exclui os valores que ``in_values`` já reivindicou
    no mesmo INMS. Categorias sobrepostas são rejeitadas para impedir que uma
    linha seja contada mais de uma vez.

    Args:
        entries: Pares de chave da categoria e modo de seleção.
        real_values: Valores reais de ``Grupo_executor`` encontrados no CSV.

    Returns:
        Uma tupla com os valores por categoria e os valores residuais de
        ``outros``.

    Raises:
        ValueError: Se categorias se sobrepuserem ou um modo não tiver o
            critério obrigatório.
    """
    seen_in_values: dict[str, str] = {}
    for categoria_key, entry in entries:
        if entry.in_values is None:
            continue
        for value in entry.in_values:
            if value in seen_in_values:
                raise ValueError(
                    f'Grupo_executor {value!r} aparece em mais de uma '
                    f'categoria ({seen_in_values[value]!r} e '
                    f'{categoria_key!r}); categorias devem ser disjuntas, '
                    'nenhuma linha pode ser contada duas vezes'
                )
            seen_in_values[value] = categoria_key

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
            contains = entry.catch_all_contains
            if contains is None:
                raise ValueError(
                    f'categoria {categoria_key!r} sem in_values ou '
                    'catch_all_contains'
                )
            effective_values = {
                value for value in real_values if contains in value
            } - in_values_claimed

        overlap = effective_values & claimed_overall
        if overlap:
            raise ValueError(
                f'categoria {categoria_key!r} sobrepõe valores já '
                f'reivindicados {sorted(overlap)!r}; nenhuma linha pode '
                'pertencer a duas categorias'
            )
        claimed_overall.update(effective_values)
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
) -> list[Warning]:
    """Cria avisos para ``in_values`` ausentes do CSV bruto.

    Args:
        inms_key: Chave contratual do INMS.
        orgao: Órgão da aferição.
        competencia: Competência mensal no formato ``YYYY-MM``.
        entries: Pares de chave da categoria e modo de seleção.
        real_values: Valores reais de ``Grupo_executor`` encontrados no CSV.
        raw_csv_path: Caminho do CSV usado na verificação.

    Returns:
        Avisos prontos para registro e acumulação pelo chamador.
    """
    warnings: list[Warning] = []
    for categoria_key, entry in entries:
        if entry.in_values is None:
            continue

        unmatched = [
            value for value in entry.in_values if value not in real_values
        ]
        if not unmatched:
            continue

        prefix = (
            f'INMS {inms_key} ({orgao}/{competencia}), categoria '
            f'{categoria_key}: '
        )
        if not (set(entry.in_values) & real_values):
            message = (
                f'{prefix}in_values {unmatched!r} sem correspondência em '
                f'Grupo_executor do CSV ({raw_csv_path}) — possível '
                'typo/renomeação, categoria ficará sem linhas'
            )
        else:
            message = (
                f'{prefix}in_values {unmatched!r} sem correspondência — '
                'valores não encontrados no CSV'
            )
        warnings.append(
            Warning(
                code='in_values_unmatched',
                message=message,
                orgao=orgao,
                competencia=competencia,
                inms_key=inms_key,
                categoria=categoria_key,
                target=WarningTarget(
                    family='categorias',
                    orgao=orgao,
                    path=(
                        'config',
                        'categorias',
                        categoria_key,
                        'inms',
                        inms_key,
                        'in_values',
                    ),
                ),
            )
        )
    return warnings


def outros_warning(
    *,
    inms_key: str,
    orgao: str,
    competencia: str,
    outros_count: int,
) -> Warning:
    """Cria o aviso para linhas não classificadas em uma categoria."""
    return Warning(
        code='outros_leftover',
        message=(
            f'INMS {inms_key} ({orgao}/{competencia}), categoria outros: '
            f'{outros_count} linha(s) não classificada(s) em nenhuma '
            'categoria — revisar categorias.yaml'
        ),
        orgao=orgao,
        competencia=competencia,
        inms_key=inms_key,
        categoria='outros',
    )
