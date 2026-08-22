# 19 — B-02: O caminho completo da origem pode expor estrutura interna

**Severidade:** Baixa

**Status:** resolved

## Problema

`f"{raw_csv_path} ({len(rows)} registros brutos)"` grava o caminho completo, que
pode revelar usernames, diretórios internos ou estrutura de rede.

## Correção recomendada

Gravar apenas `raw_csv_path.name`, ou tornar a exposição do caminho completo
configurável.

## Critério de aceite

- [x] Nota da fonte usa apenas o nome do arquivo por padrão
- [x] Teste garante que o caminho absoluto não aparece na célula gerada

## Answer

Trocado `f"{raw_csv_path} ..."` por `f"{raw_csv_path.name} ..."` na Seção 1
("Fonte dos dados:"). Não foi adicionada opção configurável para expor o
caminho completo — nenhum caso de uso identificado precisa disso, e a
correção recomendada já apontava isso como alternativa, não requisito.

Teste: `test_source_note_does_not_expose_full_path` em
`tests/test_inms_1_1_audit.py`, confirmando que `str(data_dir)` (o diretório
absoluto usado na fixture) não aparece na célula, mas `"inms-01.csv"` sim.
