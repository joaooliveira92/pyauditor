Type: grilling
Status: resolved

## Question

A CLI é um comando único que faz bootstrap da capa + execução + consolidação em sequência, ou subcomandos explícitos? O bootstrap do Excel de capa precisa ser idempotente (nunca recriar se já existir, a não ser que o usuário delete).

## Answer

**3 subcomandos explícitos**, mais um comando guarda-chuva opcional que os chama em sequência:
- `bootstrap` — cria o Excel de capa do contrato (gestor, SEI, etc.) se não existir; idempotente, nunca recria se já existir.
- `measure <competência>` — roda os indicadores configurados, gera um ROM Markdown por indicador.
- `report <competência>` — lê os ROMs + Excel de capa, gera a planilha Excel final consolidada.

Motivo: o fiscal técnico pode precisar rodar `measure` várias vezes num mês (novos CSVs chegando) sem reconsolidar toda vez; a separação facilita testar cada fase isoladamente.
