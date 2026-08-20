# Severidade de revisao

- **P0 Critical**: exploracao, perda ampla de dados, indisponibilidade sistemica ou credenciais expostas. Bloqueia merge.
- **P1 High**: bug provavel em caminho principal, autorizacao incorreta, race relevante, transacao inconsistente ou incompatibilidade grave. Bloqueia merge.
- **P2 Medium**: falha sob condicao plausivel, observabilidade insuficiente, teste critico ausente ou degradacao operacional. Corrigir antes do merge, salvo decisao registrada.
- **P3 Low**: melhoria localizada de clareza, manutencao ou eficiencia sem risco imediato. Pode virar follow-up.
- **Nit**: preferencia cosmetica opcional. Nunca apresentar como requisito.
