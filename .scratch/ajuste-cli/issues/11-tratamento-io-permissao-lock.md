# 11 - Tratamento de diretório sem permissão / arquivo bloqueado

Type: grilling
Status: resolved
Blocked by:

## Question

Hoje `PermissionError` (diretório sem permissão de escrita) e arquivo Excel aberto/bloqueado por outro processo (`.xlsx` locked no Windows) não têm tratamento dedicado em lugar nenhum do código — propagam como exceção genérica não capturada. Isso é aceitável (deixar o traceback Python subir) ou deveria virar um `_error`/`ReportResult`/`ConsolidateResult` com mensagem acionável, como as demais falhas técnicas do pipeline (ticket 03, exit code `1`)?

Questões em aberto:

- **Vale a pena capturar `PermissionError`/`OSError` de escrita especificamente**, com uma mensagem tipo "sem permissão de escrita em X — verifique as permissões do diretório", em vez de deixar o traceback subir cru? Isso mudaria a experiência de quem roda `run` sem privilégios, mas é código novo em vários pontos de escrita (`atomic_write`, `bootstrap_capa_csv`, `build_report`/`build_consolidated_workbook`).
- **Arquivo Excel aberto/bloqueado**: no Windows, abrir um `.xlsx` já aberto no Excel para escrita lança `PermissionError` do SO — é o mesmo caso do item acima, ou merece uma mensagem própria ("feche o arquivo X antes de rodar de novo")? Detectar "é lock de arquivo aberto" vs. "é permissão de diretório" de forma portável (POSIX/Windows) pode não ser possível de forma confiável.
- **`atomic_write` já garante que uma falha no meio da escrita não deixa arquivo parcial** (`test_atomic_write.py`) — a lacuna aqui é só a *mensagem* para o usuário, não a integridade do artefato.
- Vale a pena esse esforço para um CLI de uso mensal por um fiscal técnico, ou é engenharia demais para um caso raro que hoje já falha de forma segura (só com traceback feio)?

Contexto: review.md §"Operação" ("diretório sem permissão", "arquivo Excel aberto ou bloqueado"); graduado da névoa do mapa (ajuste-cli) ao fechar o ticket 09 (suíte de testes) e constatar que não há tratamento implementado para testar.

## Answer

1. **Vale o esforço, escopo mínimo**: sim, mas sem inventar detecção de causa — um `except OSError` genérico convertido em mensagem acionável nos pontos que já existem.
2. **Sem mensagem própria para "Excel bloqueado" vs "sem permissão"**: mensagem única combinada, já que a exceção não distingue as duas causas de forma confiável.
3. **Onde plugar**: nenhum try/except novo foi necessário — o levantamento de código mostrou que **todos** os pontos de escrita relevantes (bootstrap, `build_report`, `build_consolidated_workbook`, ROMs do `measure`) já capturam `OSError` e convertem em resultado estruturado (`status="error"` + `error_message`). O único ponto cru é o `atomic_write` de baixo nível, por design — cada chamador decide a mensagem. O trabalho real foi só enriquecer as mensagens já existentes com a dica acionável.
4. **`glosa_historico.json` (achado lateral)**: cogitei escalar a falha de escrita do histórico de `warning` para `status="error"` (comprometeria o rollover do mês seguinte silenciosamente), mas **revertido** — nesse ponto o `.xlsx` do relatório já foi escrito com sucesso; escalar acionaria a cascata de `isolate` do ticket 08 (pularia `consolidate`) por uma falha que não afeta o relatório em si. Mantido como warning, só com a mensagem melhorada — mudar a visibilidade, não o código de saída.

**Implementado no código**: `cli/results.py::WRITE_FAILURE_HINT`/`DIR_FAILURE_HINT` (constantes compartilhadas), aplicadas em `cli/bootstrap.py`, `cli/report.py` (escrita do relatório + histórico de glosa), `cli/consolidate.py`, `cli/measure.py` (criação de diretório + escrita de ROM, individual e combinado). Testes: um por ponto de escrita em `test_cli_bootstrap.py`/`test_cli_report.py`/`test_cli_consolidate.py`/`test_cli_measure.py`, forçando `PermissionError` via mock e checando a dica na mensagem. Suíte completa: 303 passed (também corrigida uma flakiness pré-existente no teste de idempotência do ticket 08 — comparava bytes crus de `.xlsx`, que embute timestamp; trocado por comparação de conteúdo). mypy e ruff limpos.
