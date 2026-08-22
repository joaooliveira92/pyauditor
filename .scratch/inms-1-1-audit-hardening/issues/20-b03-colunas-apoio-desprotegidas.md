# 20 — B-03: Colunas de apoio não estão ocultas nem protegidas

**Severidade:** Baixa

**Status:** needs-triage

## Problema

O texto da planilha instrui a não excluir nem reordenar as colunas de apoio
(R:AM), mas nada impede a alteração — depende só de boa vontade de quem edita.

## Correção recomendada

- Ocultar as colunas R:AM
- Proteger a planilha
- Desbloquear apenas campos de justificativa e evidência
- Opcionalmente, mover os dados de apoio para uma aba dedicada

## Critério de aceite

- [ ] Colunas R:AM ocultas por padrão
- [ ] Proteção de planilha aplicada, com campos de justificativa/evidência desbloqueados
- [ ] Teste (ou verificação manual documentada) confirmando que a proteção não quebra a leitura das fórmulas pelo pipeline
