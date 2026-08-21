# Config de indicador por categoria é gerada pelo `split`, não escrita à mão

Cada Categoria de um INMS segmentado por Grupo executor gera uma medição independente, sobre o mesmo shape de cálculo e a mesma meta do indicador base (ver `CONTEXT.md`, termo Categoria) — só o subconjunto de linhas de entrada muda. Para expressar isso sem alterar o `measure` existente, cogitamos exigir uma YAML de indicador mantida à mão por categoria, ao lado de `categorias.yaml`. Decidimos em vez disso que o passo `split` **gera** essa YAML (copiando `quality_gates`/`calculation`/`target`/`penalty` do indicador base, trocando só `id` e a fonte de dados), com um padrão de nome reservado que o `measure` já descobre pelo glob existente. Isso evita que a config por categoria fique dessincronizada do indicador base quando o Anexo D mudar — o mesmo risco que levou o ticket 02 a resolver `catch_all_contains` em runtime em vez de hardcoded.

## Opções consideradas

- **Config por categoria escrita à mão**: mantém `measure` igualmente inalterado, mas duplica `quality_gates`/`calculation`/`target`/`penalty` em N arquivos por INMS segmentado, arriscando divergência silenciosa do indicador base.
- **Alterar `measure` para aceitar filtro de categoria inline**: evita gerar arquivos, mas quebra a restrição de manter `measure` inalterado e acopla a lógica de categoria a um componente que hoje não sabe nada sobre `Grupo_executor`.
