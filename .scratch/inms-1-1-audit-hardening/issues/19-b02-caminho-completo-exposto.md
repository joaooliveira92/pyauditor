# 19 — B-02: O caminho completo da origem pode expor estrutura interna

**Severidade:** Baixa

**Status:** needs-triage

## Problema

`f"{raw_csv_path} ({len(rows)} registros brutos)"` grava o caminho completo, que
pode revelar usernames, diretórios internos ou estrutura de rede.

## Correção recomendada

Gravar apenas `raw_csv_path.name`, ou tornar a exposição do caminho completo
configurável.

## Critério de aceite

- [ ] Nota da fonte usa apenas o nome do arquivo por padrão
- [ ] Teste garante que o caminho absoluto não aparece na célula gerada
