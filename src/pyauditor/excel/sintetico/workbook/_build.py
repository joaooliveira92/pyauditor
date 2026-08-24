"""`sintetico.xlsx` (spec §14.4, ticket 05) — um workbook por órgão/
competência, uma aba por INMS com entrada em `categorias.yaml`, mais as abas
institucionais Capa/Equipe/Prazos de `input/{capa,equipe,prazos}.csv`.

`write_sintetico_workbook` é o único ponto de orquestração deste pacote:
cria o workbook, escreve as abas institucionais, agrupa `categorias.yaml`
por INMS (`_grouping`) e delega cada aba de INMS a `_render.render_inms_sheet`
— que decide o renderer por-shape (`_sheets/`) e acumula os warnings dessa
aba. Contagens são brutas/pré-quality-gate — conferência rápida, não
substitui o ROM da categoria. A única exceção é `Tempo médio
criação→resolução`, restrito às linhas aprovadas pelo quality gate,
conforme a spec.

O pacote é dividido por responsabilidade:
- `_types`: constantes e o alias `InmsEntries` compartilhados pelos demais
  módulos.
- `_grouping`: inverte `categorias.yaml` (por categoria) para por-INMS.
- `_config`: carrega e corrige (`inject_orgao`) a config base de um INMS.
- `_render`: decide e escreve a aba de um único INMS — a única parte que
  fala com `measurement_source` e os renderers de `_sheets/`.
- `_build` (este módulo): cria o workbook, escreve as institucionais, chama
  `_render` para cada INMS e grava o arquivo.

INMS 1.1 tem renderer dedicado em `excel/inms_1_1_audit.py` (fachada do
pacote `inms_1_1/`): resumo executivo, memória de cálculo, incidentes fora
do prazo e auditoria do prazo contratual via fórmulas do Excel sobre os
dados brutos embutidos na própria aba. Só entra em jogo quando o CSV bruto
tem as colunas de detalhe de produção (`Nº Solicitacao`, `Atividades`,
`DataHoraLimite`, `TecnicoExecutor` — ver
`inms_1_1_audit.has_required_columns`), decisão tomada dentro de `_render`.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Final

from openpyxl import Workbook

from pyauditor.atomic_write import atomic_write
from pyauditor.config.categorias import CategoriasFile
from pyauditor.config.manifest import DatasetManifest
from pyauditor.excel.sintetico._sheets.institutional import (
    write_institutional_sheets,
)
from pyauditor.periodo import PeriodoAfericao

from ._grouping import group_entries_by_inms
from ._render import render_inms_sheet

__all__: Final[tuple[str, ...]] = ('write_sintetico_workbook',)


def write_sintetico_workbook(
    categorias_file: CategoriasFile,
    config_dir: Path,
    competencia_data_dir: Path,
    output_path: Path,
    *,
    orgao: str = 'MinC',
    manifest: DatasetManifest | None = None,
    periodo: PeriodoAfericao | None = None,
    strict: bool = False,
    prazos_path: Path | None = None,
    capa_path: Path | None = None,
    dados_contratuais_path: Path | None = None,
    equipe_path: Path | None = None,
    perfis_profissionais_path: Path | None = None,
    objetos_path: Path | None = None,
    localidades_path: Path | None = None,
    generated_at: datetime | None = None,
) -> list[str]:
    """Constrói e grava `sintetico.xlsx` de um órgão/competência. Devolve
    warnings (nunca lança por causa do problema de um único INMS — um
    config ruim ou um dataset genuinamente ausente pula/degrada a aba
    daquele INMS em vez de derrubar o workbook inteiro).

    `orgao` corrige `scope.orgao`/`scope.contract` da config base antes de
    usá-la (via `inject_orgao`) — sem isso, uma config single-source vinda
    de `configs/_shared/` (sem `scope:` próprio) sempre exibiria o órgão/
    contrato default do modelo (MinC) na Seção 1 do INMS 1.1, mesmo ao
    gerar o `sintetico.xlsx` de outro órgão.

    `generated_at` (default `datetime.now()`, resolvido uma única vez aqui)
    é repassado à aba enriquecida do INMS 1.1 — injetável para permitir
    teste determinístico sem depender do relógio real (ticket 18 / B-01)."""
    warnings: list[str] = []
    generated_at = generated_at if generated_at is not None else datetime.now()

    per_inms = group_entries_by_inms(categorias_file)

    workbook = Workbook()
    default_sheet = workbook.active
    if default_sheet is None:
        raise RuntimeError('workbook novo sem aba ativa (openpyxl)')
    workbook.remove(default_sheet)

    write_institutional_sheets(
        workbook,
        capa_path=capa_path,
        dados_contratuais_path=dados_contratuais_path,
        objetos_path=objetos_path,
        equipe_path=equipe_path,
        perfis_profissionais_path=perfis_profissionais_path,
        prazos_path=prazos_path,
        localidades_path=localidades_path,
        warnings=warnings,
    )
    sheets_before_inms = set(workbook.sheetnames)

    for inms_key in sorted(per_inms, key=lambda k: int(k.split('.')[1])):
        warnings.extend(
            render_inms_sheet(
                workbook,
                inms_key,
                per_inms[inms_key],
                categorias_file,
                config_dir,
                competencia_data_dir,
                manifest,
                periodo,
                strict,
                orgao,
                generated_at,
            )
        )

    if set(workbook.sheetnames) == sheets_before_inms:
        # Nada pôde ser medido (todo INMS de categorias.yaml falhou ao
        # carregar/resolver) — um xlsx sem nenhuma aba de INMS não é um
        # arquivo válido pra este propósito; não sobrescreve um
        # sintetico.xlsx de rerun anterior com um arquivo vazio/quebrado.
        return warnings

    atomic_write(output_path, workbook.save)
    return warnings
