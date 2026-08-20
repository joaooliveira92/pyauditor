# Map: pyauditor — auditoria de capacidades do framework

Label: wayfinder:map

## Destination

Para cada lacuna identificada na auditoria de 2026-08-19 (abaixo), uma decisão registrada: implementar (com ticket de escopo), descartar deliberadamente, ou confirmar que segue em fog aguardando dado externo (Termo de Referência, fiscalização, dataset real). Este mapa não é sobre construir tudo — é sobre não perder o inventário de lacunas conhecidas e dar a cada uma um destino explícito.

## Notes

- Auditoria feita comparando: (1) `docs/spec/inms-pipeline.md` (spec implementada), (2) `docs/spreadsheet.md` (spec de planilha, mais ambiciosa que o implementado), (3) `inspiration-spreadsheet/afericao_06_2026.xlsx` (mockup de referência trazido pelo usuário, ainda mais amplo que `docs/spreadsheet.md`), (4) o código real em `src/pyauditor/`.
- Implementado hoje: CLI com `bootstrap`/`measure`/`report`; engine de 4 shapes (`ratio`, `segmented_ratio`, `count_difference`, `external_catalog_sum`); Excel final com `CAPA_E_CONTROLE` (aba 1, adicionada nesta sessão) + `INMS_BASE` + 4 abas de grupo + `GLOSAS`.
- Escopo atual é mono-órgão (MinC) — ver [[project-multi-org-architecture]] na memória: o usuário roda MinC e MTur como dois clones de repositório separados, unidos só depois que ambos tiverem relatório final. Isso torna `src/pyauditor/excel/orgao_consolidation.py` (que já pooled MinC+MTur *dentro* de uma única run) potencialmente órfão do fluxo real — ver ticket 07.
- Sem CI de teste/lint (`.github/workflows/docs.yml` existe, mas só publica o portal Zensical), sem linter configurado (só `mypy --strict` + `pytest`) — ver [[08-lacunas-operacionais]].

## Decisions so far

- [orgao_consolidation.py pode estar desalinhado com o fluxo real de dois repositórios](issues/07-orgao-consolidation-desalinhado.md) — `Status: resolved`. O pooling saiu de dentro do `report` e virou a base do subcomando `consolidate` (2.1, ver `.scratch/multi-org-pipeline/`). `with_orgao_consolidation` hoje só é chamado por `src/pyauditor/excel/consolidate.py`, nunca por `cli/report.py`.
- [Cadastros: aba de dados de referência](issues/09-cadastros-aba-de-dados-de-referencia.md) — `Status: closed`, implementada (`CADASTROS_SHEET` em `report.py`).
- [Evidências: registro de provas](issues/10-evidencias-registro-de-provas.md) — `Status: closed`, implementada (`EVIDENCIAS_SHEET` em `report.py`).
- [Abas do mockup não implementadas](issues/01-abas-nao-implementadas.md) — `Status: resolved`. CADASTROS/EVIDENCIAS saíram do fog (09/10 acima); CALCULO_PAGAMENTO e SERVICOS_POR_ORGAO confirmadas implementadas dentro do `consolidate` (`CALCULO_SHEET`/`SERVICOS_SHEET` em `consolidate.py`); PAINEL_GERENCIAL, HISTORICO, CHECKLIST_FISCAL, RELATORIO_FISCAL e FONTES_E_PREMISSAS foram para **out of scope** no mapa `multi-org-pipeline`. Nenhuma aba da lista original ficou pendente.
- [Fórmula de consolidação MinC/MTur para disponibilidade por ativo (1.4/1.5/1.14)](issues/06-formula-consolidacao-per-asset.md) — `Status: resolved` (como decisão, não como pesquisa concluída). Fórmula do TR continua não localizada; decidido manter por-ativo uma linha por órgão, sem consolidar, até o TR definir. Fog deliberado — reabrir só se surgir fonte primária nova.
- [Rollover de glosa entre competências não é lido de volta](issues/02-rollover-glosa-nao-consumido.md) — `Status: resolved`. Item 35 do TR confirma que o excedente acima do teto de 30% deve rolar para a fatura do mês seguinte (exceto no último mês de vigência) — é requisito real, não efeito colateral do mockup. `saldo_rolado_pct` é calculado mas não consumido hoje. Vira decisão de implementação em [[11-estado-persistente-entre-competencias]].
- [Reincidência (repeat offense) não é rastreada](issues/03-reincidencia-nao-rastreada.md) — `Status: resolved`. TR não define multiplicador de glosa por reincidência — define um gatilho separado: estourar o teto de 30% três vezes em 6 meses vira "inexecução parcial do contrato" (sanção administrativa, fora do cálculo monetário). Mesma necessidade de estado entre competências, ver [[11-estado-persistente-entre-competencias]].
- [Teto anual de glosa não verificado](issues/04-teto-anual-glosa.md) — `Status: resolved`. Não existe teto anual operável — só o teto mensal de 30% com rollover. Há uma segunda fórmula "Anual" no TR com termos (`RB`, `Desconto Máximo Anual`) nunca definidos em nenhum outro lugar do documento — cheiro de boilerplate de template não adaptado; não implementar até o gestor confirmar. `CAP_PCT = 30.0` em `glosas.py` já está correto, sem mudança de código necessária.
- [Estado persistente entre competências: rollover de glosa + reincidência](issues/11-estado-persistente-entre-competencias.md) — `Status: resolved`, **implementado**. Ledger JSON por órgão (`roms/<orgao>/glosa_historico.json`), `compute_glosa` ganha `saldo_anterior_pct`, aba `GLOSAS` ganha colunas "Saldo recebido do mês anterior" e "Reincidência (3x/6m)?". `is_final_month` virou flag explícita `--final-month` no `report` (não derivado da `Vigência` da capa — campo é texto livre sem formato definido, desvio do desenho original). 131 testes passando.
- [Lacunas operacionais: pré-validação, CI, relatório narrativo](issues/08-lacunas-operacionais.md) — `Status: resolved`. Decisão: aceito como processo manual permanente para os quatro itens (pré-validação da capa, CI real de teste/lint, sugestão automática de "situação geral", relatório narrativo assinável). Nenhum código implementado; reabrir só sob pressão real.
- [Fonte de dados real do INMS 1.8/1.10 ainda não confirmada](issues/05-fonte-dados-inms-1-8-1-10.md) — `Status: resolved` (reenquadrado + fonte primária localizada). RAS oficial de junho/2026 confirma CITSmart como ferramenta de conferência da aferição mensal; cross-check por indicador mostra que **INMS 1.14 já é dado real** (bate exatamente com o RAS — seis serviços, 98,49% agregado), rótulo "Dados sinteticos" em `inms-14.csv` era obsoleto e foi corrigido. INMS 1.4/1.8/1.10 seguem sem confirmação por indicador — RAS só dá valor agregado para 1.4, nenhuma tabela para 1.8/1.10. Gap remanescente: fiscalização confirmar se o schema de `inms-1.8.yaml`/`inms-1.10.yaml` é o que será preenchido de fato.

## Not yet specified

(vazio)

## Out of scope

- Reproduzir as 17 abas da planilha de inspiração além do núcleo financeiro — decidido no mapa `multi-org-pipeline`: `CHECKLIST_FISCAL`, `RELATORIO_FISCAL`, `PAINEL_GERENCIAL`, `HISTORICO` ficam fora (ver ticket 01 acima).
- Fórmula de consolidação por-ativo (1.4/1.5/1.14) — mantida por-órgão até o TR definir (ver ticket 06 acima).
