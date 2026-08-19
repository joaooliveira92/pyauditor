# Map: pyauditor — auditoria de capacidades do framework

Label: wayfinder:map

## Destination

Para cada lacuna identificada na auditoria de 2026-08-19 (abaixo), uma decisão registrada: implementar (com ticket de escopo), descartar deliberadamente, ou confirmar que segue em fog aguardando dado externo (Termo de Referência, fiscalização, dataset real). Este mapa não é sobre construir tudo — é sobre não perder o inventário de lacunas conhecidas e dar a cada uma um destino explícito.

## Notes

- Auditoria feita comparando: (1) `docs/spec/inms-pipeline.md` (spec implementada), (2) `docs/spreadsheet.md` (spec de planilha, mais ambiciosa que o implementado), (3) `inspiration-spreadsheet/afericao_06_2026.xlsx` (mockup de referência trazido pelo usuário, ainda mais amplo que `docs/spreadsheet.md`), (4) o código real em `src/pyauditor/`.
- Implementado hoje: CLI com `bootstrap`/`measure`/`report`; engine de 4 shapes (`ratio`, `segmented_ratio`, `count_difference`, `external_catalog_sum`); Excel final com `CAPA_E_CONTROLE` (aba 1, adicionada nesta sessão) + `INMS_BASE` + 4 abas de grupo + `GLOSAS`.
- Escopo atual é mono-órgão (MinC) — ver [[project-multi-org-architecture]] na memória: o usuário roda MinC e MTur como dois clones de repositório separados, unidos só depois que ambos tiverem relatório final. Isso torna `src/pyauditor/excel/orgao_consolidation.py` (que já pooled MinC+MTur *dentro* de uma única run) potencialmente órfão do fluxo real — ver ticket 07.
- Sem CI (`.github/` não existe), sem linter configurado (só `mypy --strict` + `pytest`).

## Decisions so far

- [orgao_consolidation.py pode estar desalinhado com o fluxo real de dois repositórios](issues/07-orgao-consolidation-desalinhado.md) — `Status: resolved`. O pooling saiu de dentro do `report` e virou a base do subcomando `consolidate` (2.1, ver `.scratch/multi-org-pipeline/`). `with_orgao_consolidation` hoje só é chamado por `src/pyauditor/excel/consolidate.py`, nunca por `cli/report.py`.
- [Cadastros: aba de dados de referência](issues/09-cadastros-aba-de-dados-de-referencia.md) — `Status: closed`, implementada (`CADASTROS_SHEET` em `report.py`).
- [Evidências: registro de provas](issues/10-evidencias-registro-de-provas.md) — `Status: closed`, implementada (`EVIDENCIAS_SHEET` em `report.py`).
- [Abas do mockup não implementadas](issues/01-abas-nao-implementadas.md) — `Status: resolved`. CADASTROS/EVIDENCIAS saíram do fog (09/10 acima); CALCULO_PAGAMENTO e SERVICOS_POR_ORGAO confirmadas implementadas dentro do `consolidate` (`CALCULO_SHEET`/`SERVICOS_SHEET` em `consolidate.py`); PAINEL_GERENCIAL, HISTORICO, CHECKLIST_FISCAL, RELATORIO_FISCAL e FONTES_E_PREMISSAS foram para **out of scope** no mapa `multi-org-pipeline`. Nenhuma aba da lista original ficou pendente.
- [Fórmula de consolidação MinC/MTur para disponibilidade por ativo (1.4/1.5/1.14)](issues/06-formula-consolidacao-per-asset.md) — `Status: resolved` (como decisão, não como pesquisa concluída). Fórmula do TR continua não localizada; decidido manter por-ativo uma linha por órgão, sem consolidar, até o TR definir. Fog deliberado — reabrir só se surgir fonte primária nova.

## Partially addressed

- [Lacunas operacionais: pré-validação, CI, relatório narrativo](issues/08-lacunas-operacionais.md) — ainda `open`. Único fato novo: `.github/workflows/docs.yml` existe, mas é publicação do portal Zensical, não CI de teste/lint. Pré-validação da capa, sugestão automática de "situação geral" e relatório narrativo seguem sem código.

## Not yet specified

- [Rollover de glosa entre competências não é lido de volta](issues/02-rollover-glosa-nao-consumido.md) — sem progresso, depende do Termo de Referência.
- [Reincidência (repeat offense) não é rastreada](issues/03-reincidencia-nao-rastreada.md) — sem progresso, depende do Termo de Referência.
- [Teto anual de glosa não verificado](issues/04-teto-anual-glosa.md) — sem progresso, depende do Termo de Referência.
- [Fonte de dados real do INMS 1.8/1.10 ainda não confirmada](issues/05-fonte-dados-inms-1-8-1-10.md) — sem progresso, depende de resposta externa (fiscalização/gestor do contrato).

## Out of scope

- Reproduzir as 17 abas da planilha de inspiração além do núcleo financeiro — decidido no mapa `multi-org-pipeline`: `CHECKLIST_FISCAL`, `RELATORIO_FISCAL`, `PAINEL_GERENCIAL`, `HISTORICO` ficam fora (ver ticket 01 acima).
- Fórmula de consolidação por-ativo (1.4/1.5/1.14) — mantida por-órgão até o TR definir (ver ticket 06 acima).
