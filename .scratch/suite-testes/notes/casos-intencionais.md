# Casos intencionais de junção sem espaço (ticket 03)

Revisão de todas as ~90 costuras encontradas (82 por fronteira de literais
concatenados implicitamente + ~10 já fundidas num único literal pelo
`ruff format`, achadas por varredura de padrão camelCase e por triagem dos
testes que ainda falhavam). **Nenhum caso legítimo de colagem intencional foi
encontrado** — todas eram regressão acidental do refactor (texto pt-BR/en
partido sem espaço na junção, incluindo nomes de campo usados como chave de
dicionário como `"Fiscalrequisitante"` em `rom/render.py`).

Não há, portanto, exceções a documentar como insumo para o ticket 02 —
`allow-multiline = false` pode ser ligado sem `per-file-ignores` adicionais
motivados por este levantamento.
