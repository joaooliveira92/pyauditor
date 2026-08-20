Type: grilling
Status: resolved

## Question

A cadeia bootstrap→measure→report→consolidate hoje é só convenção (nada no código impede rodar `report` sem `measure` ter rodado antes, ou `consolidate` sem os dois relatórios por órgão). Decisão de fundação (map.md) já travou que essa cadeia passa a ser validada por uma camada de orquestração compartilhada, usada pelos dois modos (interativo e não-interativo) — "impedir combinações inválidas" é requisito explícito do pedido original.

Decidir:

- Onde essa validação vive fisicamente (novo módulo, ex. `src/pyauditor/orchestration/dependencies.py`? dentro de `cli/`? um pacote novo?) — sem violar a separação pipeline/apresentação.
- Como cada Command declara suas dependências (lista estática por Command, ex. `report` depende de `measure` ter Command state `done` para o mesmo `(competencia, orgao)`?) e como isso se verifica na prática — arquivo de output existe? JSON sidecar é válido? consulta ao run-state (ticket "Orquestrador `pyauditor run` + resumibilidade")?
- Comportamento quando a dependência falta: erro claro e bloqueio sempre, ou existe uma saída de escape (`--force`/`--skip-checks`) para quem sabe o que está fazendo (ex.: já rodou `measure` manualmente fora do fluxo e só quer reexecutar `report`)?
- Isso é checado uma vez no início do Run inteiro, ou a cada Command individualmente antes de rodar (relevante se o usuário roda comandos fora de ordem manualmente, um de cada vez, dias depois)?

## Answer

- **Fonte de verdade**: estado do filesystem (padrão já existente — capa existe, ROMs dir tem sidecars JSON, arquivos de relatório por órgão existem), **não** o run-state do ticket "Run orchestrator and resume" (ainda não resolvido). Run-state vira um cache de retomada por cima disso depois, nunca o mecanismo de aplicação — desacopla este ticket do schema ainda em aberto do ticket 03.
- **Localização física**: um módulo de registro fino (`src/pyauditor/cli/dependencies.py`) mapeando cada Command à sua função checadora; a lógica de precondição em si fica colocada no arquivo de cada comando (`check_report_ready` em `report.py`, `check_consolidate_ready` em `consolidate.py`, etc.) — espelha o precedente de colocação do ticket "Structured result dataclasses".
- **Dois pontos de chamada, uma implementação**: a mesma função checadora compartilhada é chamada (a) no ponto de despacho (`cli_main`, depois o orquestrador/camada interativa) *antes* de invocar `run_*` — erro rápido e acionável, e permite a camada interativa apagar/bloquear seleções inválidas antes de tentar; e (b) *dentro* de cada `run_*`, como guarda de defesa-em-profundidade para chamadores que contornam o ponto de despacho (testes unitários chamando `run_report` diretamente, código futuro). Nunca reimplementada duas vezes — é a mesma função, dois call sites.
- **Correção sobre o enunciado do ticket**: `report` não depende só de `measure` — `report.py:37` também checa `capa_path.exists()`, que é saída do `bootstrap`. E `consolidate` não depende de "o mesmo Command para o mesmo órgão" — depende de `report` (e das ROMs de `measure`) para **os dois** órgãos, MinC e MTur, um par fixo, não um predecessor genérico por `(competencia, orgao)`.
- **Formato da declaração**: não uma tabela genérica `Command → tuple[Command, ...]` (não expressa "os dois órgãos" nem "duas Commands anteriores diferentes" sem virar uma mini-linguagem própria). Em vez disso, uma função checadora por Command, assinatura própria, retornando um tipo pequeno compartilhado:

```python
@dataclass(frozen=True, slots=True)
class DependencyCheck:
    satisfied: bool
    missing: tuple[str, ...]

# report.py
def check_report_ready(competencia: str, orgao: str, capa_path: Path, roms_dir: Path) -> DependencyCheck: ...
    # capa_path.exists() (bootstrap) + (roms_dir / competencia).is_dir() com sidecars (measure)

# consolidate.py
def check_consolidate_ready(competencia: str, report_dir: Path, roms_dir: Path) -> DependencyCheck: ...
    # relatorio_<comp>_MinC.xlsx + _MTur.xlsx existem, roms_dir/MinC/<comp> e /MTur/<comp> existem

# measure.py / bootstrap.py
def check_measure_ready(...) -> DependencyCheck: ...  # sempre satisfied=True, sem dependências
def check_bootstrap_ready(...) -> DependencyCheck: ...  # idem
```

Extraídas quase literalmente das checagens ad-hoc já existentes em `report.py:37,42` e `consolidate.py:39-56` — não é lógica nova, é a mesma lógica nomeada e compartilhada.

- **Sem escape hatch**: nenhum `--force`/`--skip-checks` por enquanto — nenhuma necessidade concreta surgiu, e é exatamente o tipo de flag especulativa que "não construir para requisito hipotético futuro" descarta. Se aparecer uma necessidade real, volta como fog em **Not yet specified**, não como algo construído preventivamente.
- **Timing**: sempre imediatamente antes de despachar um Command — nunca uma checagem única no início do Run inteiro. Uma checagem no início do Run falharia para `report` antes de `measure` (enfileirado antes, no mesmo Run) sequer ter rodado. Uniforme entre invocação direta de um único comando, `pyauditor run` completo, e execução parcial/seleção de Commands.
