# 01 — Schema e dados de `categorias.yaml`

**What to build:** o mapeamento declarativo categoria→Grupo_executor→INMS descrito em
`docs/spec/inms-pipeline.md` §14.2 vira dado real e tipado: um arquivo `configs/MinC/categorias.yaml`
e um `configs/MTur/categorias.yaml`, cada um com as 4 categorias substantivas
(`ATENDIMENTO_N1`/`ATENDIMENTO_N2`/`OPERACAO_N3`/`MONITORAMENTO_NOC_SOC`) e a lista completa de INMS
por categoria da tabela do §14.2, mais um loader tipado que valida o schema em runtime.

O schema tem um campo discriminador `mode` por entrada INMS-dentro-de-categoria:
`mode: grupo_executor` (com `in_values` — reaproveitando o `ColumnIn` já existente em
`src/pyauditor/config/models.py` — ou `catch_all_contains`) ou `mode: whole_indicator` (sem filtro).

**Cuidado de nomenclatura:** já existe uma classe `SegmentedCategory` em
`src/pyauditor/config/models.py` para um conceito completamente diferente (as faixas de pontuação do
shape `segmented_ratio`). Os novos tipos deste ticket precisam de nomes que não colidam com esse —
ex.: `CategoriaGrupoExecutor`, `GrupoExecutorMode`, `WholeIndicatorMode` — não reusar "Category"/
"Categoria" sozinho como nome de classe.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Modelos Pydantic (frozen/strict/extra=forbid, seguindo o padrão de `config/models.py`) para as
      duas variantes de entrada (`grupo_executor` com `in_values` xor `catch_all_contains`;
      `whole_indicator` sem campos de filtro), com um `TypeAlias` discriminado por `mode`
- [ ] Função de loader (ex. `load_categorias(path: Path) -> ...`) que lê e valida um
      `categorias.yaml`, com testes cobrindo: schema válido, `mode` desconhecido rejeitado,
      `grupo_executor` com ambos `in_values` e `catch_all_contains` (ou nenhum) rejeitado
- [ ] `configs/MinC/categorias.yaml` preenchido com a tabela completa do §14.2 (INMS 1.1, 1.2, 1.6,
      1.7, 1.9, 1.11, 1.12, 1.13, 1.14 conforme mapeamento; 1.6-no-MinC em `whole_indicator` só em
      `OPERACAO_N3`, sem duplicar em `ATENDIMENTO_N1`/`N2`)
- [ ] `configs/MTur/categorias.yaml` preenchido com a mesma tabela, mas com os literais de
      `Grupo_executor` reais do MTur (diferentes dos do MinC — ver ticket 02 do mapa de decisões);
      1.6 no MTur usa `mode: grupo_executor` (tem a coluna real lá, ao contrário do MinC)
- [ ] 1.8 e 1.10 não têm entrada em nenhum dos dois arquivos (implícito — sem categoria)
- [ ] `uv run mypy --strict src` e `uv run pytest` verdes
