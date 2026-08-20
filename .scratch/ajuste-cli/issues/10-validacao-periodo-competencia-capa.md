# 10 - Validação de período/competência na capa

Type: grilling
Status: resolved
Blocked by:

## Question

O ticket 02 já decidiu a **intenção**: "Competência: derivada do argumento CLI; se a capa traz valor, deve coincidir (divergência = WARNING). Períodos: deriváveis da competência (primeiro e último dia do mês); se a capa traz valores, validar coincidência com o mês." Isso nunca foi implementado — hoje `capa_{orgao}.csv` guarda "Competência", "Período inicial da aferição" e "Período final da aferição" como texto livre, sem nenhum parsing de data em lugar nenhum do código (`excel/capa.py::read_capa_csv_fields` devolve strings cruas, sem validação).

O que falta decidir para poder implementar:

- **Formato de data aceito**: o fiscal técnico preenche a mão. `DD/MM/AAAA` (convenção pt-BR) é o formato natural, mas nenhum outro campo do sistema usa datas em texto livre hoje (competência é sempre `AAAA-MM`). Aceitar só um formato ou alguns (com normalização)?
- **"Divergência = WARNING" cobre qual desalinhamento**: só competência (capa diz "2026-05", CLI roda "2026-06")? Só período fora do mês? Também período inicial > final (isso não é "divergência da competência", é um erro de digitação dentro do próprio par de campos — deveria ter uma mensagem própria)?
- **Campo vazio continua não sendo erro**: períodos/competência ausentes na capa já são cobertos por "obrigatórios para publicar" (ticket 02) — só o campo *preenchido incorretamente* é o caso novo aqui.
- **Onde plugar a checagem**: em `_load_capa_fields`/`run_report` (`cli/report.py`), no mesmo lugar que hoje só resolve os campos comuns+órgão — ou um validador dedicado reaproveitado por `report`/`consolidate`?

Contexto: review.md §"Validação da capa" ("competência divergente do argumento da CLI", "período fora da competência", "período inicial posterior ao final") e §"Sobre regras de negócio" ("Os períodos podem ser derivados automaticamente?"); ticket 02 (decisão de intenção, sem implementação); graduado da névoa do mapa (ajuste-cli) ao fechar o ticket 09 (suíte de testes) e constatar que não há o que testar sem essa decisão.

## Answer

1. **Formato**: `DD/MM/AAAA`, único formato aceito para "Período inicial/final da aferição". "Competência" na capa continua `AAAA-MM` (mesmo formato do argumento CLI), comparação textual direta.
2. **Três avisos distintos**, nunca um genérico: competência divergente do argumento CLI; período (inicial ou final, cada um sinalizado à parte) fora dos limites do mês da competência; período inicial posterior ao final.
3. **Campo vazio**: confirmado — inalterado, continua só sob a regra "obrigatório para publicar" do ticket 02. Esta decisão cobre exclusivamente o campo *preenchido mas incorreto*.
4. **Validador dedicado**: `excel/capa.py::validate_periodo_competencia(capa_fields, competencia) -> tuple[str, ...]`, mesmo espírito de `missing_publication_fields`. Só `report` chama — `consolidate` nunca leu campos por-órgão (só `capa.csv` comum, que não tem competência/período), então não há dado para validar lá; a checagem já acontece uma vez por órgão dentro de `run_report`.
5. **Malformado (não parseia DD/MM/AAAA) é WARNING**, não falha técnica — consistente com "capa incorreta não bloqueia processar" do ticket 02. Reservado para o próprio par (início > fim): quando ambos parseiam mas estão invertidos, só esse aviso é emitido (comparar contra os limites do mês não ajudaria e duplicaria o sinal).

**Sem impacto em CONTEXT.md/ADR**: "período da aferição" é o limite de calendário derivado de Competência, não um conceito de domínio novo — mesma lógica do ticket 08 (mecânica de validação, não vocabulário de negócio).

**Implementado no código**: `excel/capa.py::validate_periodo_competencia`/`_parse_data_br`/`_mes_bounds`; chamada em `cli/report.py::run_report` logo após `_load_capa_fields`. Testes: `tests/test_capa.py` (6 testes unitários do validador) + `tests/test_cli_report.py::test_run_report_warns_on_competencia_divergente_na_capa` (integração). Suíte completa: 299 passed. mypy e ruff limpos nos arquivos tocados.
