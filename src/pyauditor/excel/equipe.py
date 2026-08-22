"""`equipe.csv` — fonte única dos responsáveis da aferição (spec:
.scratch/competencia-cli-equipe §6).

A capa perdeu os 4 responsáveis; `input/equipe.csv` é a única fonte: uma
linha por função (`FUNÇÃO,NOME,SIAPE`). O mapeamento normaliza caixa e
acento — "Gestor do Contrato", "GESTOR DO CONTRATO" e "gestor do contrato"
caem todos em "Gestor do contrato". Linhas com o sufixo "Substituto" (com ou
sem hífen — "- Substituto" e "Substituto" são equivalentes) ficam no CSV
(histórico/consulta) mas nunca alimentam planilha nem ROM.

Malformado (cabeçalho errado, linha sem nome, função duplicada) é falha
técnica → `ValueError`; arquivo *ausente* é dado incompleto — decisão do
chamador (warning + campos vazios), mesmo contrato de `objetos.py`.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Final

EQUIPE_FILENAME: Final = 'equipe.csv'
EQUIPE_DELIMITER: Final = ','
EQUIPE_ENCODING: Final = 'utf-8-sig'

_FUNCAO_HEADER: Final = 'FUNÇÃO'
_NOME_HEADER: Final = 'NOME'
_SIAPE_HEADER: Final = 'SIAPE'

RESPONSAVEL_LABELS: Final[tuple[str, ...]] = (
    'Fiscal técnico',
    'Fiscal requisitante',
    'Fiscal administrativo',
    'Gestor do contrato',
)

_SUBSTITUTO_RE: Final = re.compile(r'\s*-?\s*substituto$')


def _normalize(texto: str) -> str:
    """Caixa/acento/espaço-insensível: 'FISCAL Técnico' ≡ 'fiscal tecnico'."""
    decomposto = unicodedata.normalize('NFD', texto.strip().casefold())
    sem_acento = ''.join(
        ch for ch in decomposto if not unicodedata.combining(ch)
    )
    return re.sub(r'\s+', ' ', sem_acento)


_FUNCAO_BY_NORMALIZED: Final[dict[str, str]] = {
    _normalize(label): label for label in RESPONSAVEL_LABELS
}


@dataclass(frozen=True, slots=True)
class Equipe:
    """Parsed `equipe.csv`: função normalizada → (nome, siape)."""

    membros: dict[str, tuple[str, str]]
    warnings: tuple[str, ...]

    def cell(self, funcao_canonica: str) -> str:
        """Célula `Nome (SIAPE)` para um rótulo canônico; '' quando ausente."""
        par = self.membros.get(_normalize(funcao_canonica))
        if par is None:
            return ''
        nome, siape = par
        return f'{nome} ({siape})' if siape else nome

    def responsaveis_fields(self) -> dict[str, str]:
        """Rótulos canônicos presentes → célula 'Nome (SIAPE)'."""
        campos: dict[str, str] = {}
        for label in RESPONSAVEL_LABELS:
            valor = self.cell(label)
            if valor:
                campos[label] = valor
        return campos


def read_equipe(path: Path) -> Equipe:
    """Lê e valida `equipe.csv`.

    Raises:
        FileNotFoundError: arquivo ausente — dado incompleto, o chamador
            decide (warning + campos vazios).
        ValueError: malformado — cabeçalho errado, linha sem função/nome,
            função duplicada.
    """
    with path.open(encoding=EQUIPE_ENCODING, newline='') as handle:
        reader = csv.DictReader(handle, delimiter=EQUIPE_DELIMITER)
        if reader.fieldnames is None:
            raise ValueError(f'{path}: CSV vazio ou sem cabeçalho')
        fieldnames = [name.strip() for name in reader.fieldnames]
        esperado = {_FUNCAO_HEADER, _NOME_HEADER, _SIAPE_HEADER}
        if set(fieldnames) != esperado:
            raise ValueError(
                f'{path}: cabeçalho esperado '
                f"'{','.join((_FUNCAO_HEADER, _NOME_HEADER, _SIAPE_HEADER))}'"
            )
        rows = list(reader)

    membros: dict[str, tuple[str, str]] = {}
    warnings: list[str] = []
    for row in rows:
        funcao_raw = (row[_FUNCAO_HEADER] or '').strip()
        nome = (row[_NOME_HEADER] or '').strip()
        siape = (row[_SIAPE_HEADER] or '').strip()
        if not funcao_raw and not nome and not siape:
            continue  # linha em branco residual — ignora
        if not funcao_raw:
            raise ValueError(
                f'{path}: linha sem função (nome {nome!r} sem FUNÇÃO)'
            )
        if not nome:
            raise ValueError(
                f'{path}: linha sem nome para a função {funcao_raw!r}'
            )
        chave = _normalize(funcao_raw)
        if chave in membros:
            raise ValueError(f'{path}: função duplicada: {funcao_raw!r}')
        substituto_match = _SUBSTITUTO_RE.search(chave)
        eh_substituto = substituto_match is not None
        base_chave = (
            chave[: substituto_match.start()].strip()
            if substituto_match
            else chave
        )
        if not eh_substituto and base_chave not in _FUNCAO_BY_NORMALIZED:
            warnings.append(
                f'função desconhecida {funcao_raw!r} — não mapeada para nenhum'
                f'campo da capa'
            )
        membros[chave] = (nome, siape)

    for label in RESPONSAVEL_LABELS:
        if _normalize(label) not in membros:
            warnings.append(f"sem linha para '{label}' — campo fica vazio")

    return Equipe(membros=membros, warnings=tuple(warnings))


def read_responsaveis(
    equipe_path: Path,
) -> tuple[dict[str, str], tuple[str, ...]]:
    """Conveniência para os chamadores do pipeline (`measure`/`report`/
    `consolidate`) que tratam equipe ausente/malformada como dado incompleto —
    nunca falha técnica: devolve `(campos, warnings)`, com `campos` vazio e
    warning explicativo nos dois casos de erro."""
    try:
        equipe = read_equipe(equipe_path)
    except FileNotFoundError:
        return {}, (
            f"equipe não encontrada em {equipe_path} — responsáveis ficam '[a"
            f"preencher]' "
            f'(rode'
            f'`pyauditor'
            f'bootstrap`'
            f'ou'
            f'crie'
            f'o'
            f'arquivo:'
            f'{EQUIPE_FILENAME})',
        )
    except ValueError as exc:
        return {}, (
            f"falhaaoler{equipe_path}:{exc}—responsáveisficam'[apreencher]'",
        )
    prefixo = f'{equipe_path.name}: '
    return equipe.responsaveis_fields(), tuple(
        prefixo + w for w in equipe.warnings
    )
