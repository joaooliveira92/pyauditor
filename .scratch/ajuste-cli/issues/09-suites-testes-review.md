# 09 - Suíte de testes dos cenários do review

Type: task
Status: resolved
Blocked by: 01, 02, 03, 04

## Question

Implementar os cenários de teste da seção **"Cenários de teste"** do `.scratch/ajuste-cli/review.md` como testes de regressão, agora que o contrato das decisões 01/02/03/04 travou (representação da glosa, criticidade, códigos de saída, resumo final).

Abrangência (do review):
- **Validação da capa**: capa inexistente; completa; competência ausente; competência divergente do argumento CLI; período fora da competência; período inicial > final; fiscais ausentes; valor mensal vazio/zero/negativo/formatado inválido.
- **Indicadores**: exatamente 14; ausente; duplicado; arquivo vazio; malformado; código interno divergente do arquivo; falha ao ler; valor não numérico; precisão decimal; processamento parcial.
- **Consolidação**: dois órgãos válidos; um válido + um incompleto; nenhum válido; relatório anterior inexistente; relatório anterior com decisões; preservação integral de decisões; conflito decisão anterior/nova; glosa calculável; glosa não calculável; **garantia de que não calculada nunca vira `0.00`** (ticket 01).
- **Operação**: idempotência; diretório sem permissão; arquivo Excel aberto/bloqueado; falha de escrita; escrita atômica; caminhos Windows e POSIX; interrupção durante consolidação; logs sem dados sensíveis.

Notes: os sintéticos já existentes cobrem parte; entregue como tickets de implementação nos arquivos de teste adequados; atenção à névoa "Validação de indicadores" (o "14" esperado ainda não foi decidido — não travar em 14 sem o ticket de validação).

## Answer

Levantamento completo dos ~39 cenários do review contra a suíte atual, seguido da implementação dos que testam comportamento **já decidido/existente no código** (13 testes novos). Cenários sem validação implementada no código foram propositalmente deixados de fora — escrever um teste para um comportamento inexistente inventaria contrato, o que foge do escopo de um ticket `task` (é decisão, não teste).

### Implementado (13 testes novos)

**Validação da capa** (`tests/test_objetos.py`, `tests/test_cli_report.py`):
- `test_zero_value_item_is_legitimate_not_malformed` / `test_run_report_valor_mensal_zero_is_glosa_calculada` — valor mensal `0,00` é legítimo (ticket 01: numérico, nunca confundido com "não calculada").
- `test_rejects_empty_item_value` — valor mensal vazio numa linha de item é malformado (falha técnica, mesmo caminho de `parse_brl_value`).
- `test_rejects_negative_item_value` — valor mensal negativo é malformado (regex de `parse_brl_value` não aceita `-`).
- `test_missing_publication_fields_*` (3 testes, função pura) + `test_run_report_missing_fiscais_is_rascunho_nao_publicavel` — fiscais ausentes → rascunho/não-publicável (ticket 02).

**Consolidação** (`tests/test_cli_consolidate.py`):
- `test_run_consolidate_fails_when_both_reports_are_missing` — nenhum órgão válido, mensagem cita os dois.
- `test_run_consolidate_succeeds_with_one_orgao_as_rascunho` — um válido + um incompleto (rascunho) ainda consolida (ticket 08: `check_consolidate_ready` só olha existência de arquivo).
- `test_run_consolidate_without_objetos_cells_are_none_not_zero` — estende a garantia central do ticket 01 (não calculada ≠ `0.00`) até a célula do `GLOSAS` do consolidado, não só do report.
- `test_run_consolidate_preserves_decision_despite_new_penalty_value` — "conflito entre decisão anterior e nova apuração": decisão do fiscal sobrevive a um recálculo que muda o Percentual de Ajuste da mesma ocorrência.

**Operação** (`tests/test_cli_run.py`):
- `test_run_run_repeated_execution_is_idempotent` — `run` chamado duas vezes sem mudança produz o mesmo exit code e bytes idênticos do artefato.

### Fora de escopo (sem validação implementada — não é lacuna de teste, é decisão pendente)

- **Competência divergente do argumento CLI / período fora da competência / período inicial > final**: os campos de período na capa são texto livre — não há parsing de data em nenhum lugar do código, então não há o que testar. Vira névoa nova no mapa (ver `Not yet specified`).
- **Indicador ausente/duplicado/"exatamente 14"**: já é a névoa "Validação de indicadores" do mapa — mantida, não graduada por este ticket.
- **Markdown malformado do ROM**: o `.md` do ROM é só artefato de auditoria para humano — `report` lê o `.json` do sumário, nunca o `.md` de volta. Sem código, sem teste.
- **Código interno divergente do nome do arquivo**: o nome do YAML de config é arbitrário; só `contractual_id` importa. Nenhum cross-check existe.
- **Soma com precisão decimal**: a pergunta "o projeto usa `Decimal`?" segue em aberto no review (§Perguntas para a equipe) — travar um teste de precisão agora fixaria uma resposta não decidida.
- **Processamento parcial de indicadores** ("13 de 14, segue mesmo assim"): depende da mesma validação de contagem ainda não decidida.
- **Diretório sem permissão / Excel aberto ou bloqueado**: nenhum tratamento específico de `PermissionError`/lock existe — hoje esses casos propagam como exceção genérica. Vira névoa nova.
- **Logs sem dados sensíveis**: precisa antes de uma decisão do que conta como "sensível" no domínio (CNPJ é público/contratual; nomes de fiscais talvez não) — sem essa definição, um teste automatizado não tem o que verificar. Vira névoa nova.

Suíte completa: 292 passed (era 279 no fechamento do ticket 08). mypy e ruff limpos nos arquivos tocados (achados pré-existentes nas mesmas linhas não fazem parte do diff).