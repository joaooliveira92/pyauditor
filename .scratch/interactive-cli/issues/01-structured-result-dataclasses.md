Type: grilling
Status: resolved

## Question

Hoje `run_bootstrap`/`run_measure`/`run_report`/`run_consolidate` retornam só `int` (código de saída) — decisão de fundação (map.md) já travou que isso vira um dataclass congelado de resultado, espelhando o padrão dos `Request` (`MeasureRequest` etc.), para que a camada interativa (e o futuro `pyauditor run`) tenham dados estruturados para renderizar um resumo, sem reler arquivos de saída nem duplicar lógica de negócio.

Decidir:

- Um dataclass de resultado por comando (`MeasureResult`, `ReportResult`, `ConsolidateResult`, `BootstrapResult`) ou um único formato genérico (`CommandResult`) reaproveitado pelos 4?
- Campos: no mínimo código de saída — que mais? (ex.: `run_measure` hoje sabe por-indicador se houve `hard_failure`; `run_report`/`run_consolidate` sabem contagem de indicadores e se decisões do fiscal foram preservadas; `run_bootstrap` sabe se criou a capa ou se já existia.)
- Como os `run_*` atuais mudam de assinatura sem quebrar os call-sites hoje em `cli_main` (que hoje faz `code |= run_measure(...)` bit-a-bit para o fan-out de `--orgao both`) — o `|=` deixa de fazer sentido se o retorno não é mais `int`.
- Erros: continuam sendo logados via `loguru` e retornados como resultado com status de erro (nunca exceção crua atravessando a fronteira), ou algum caso passa a propagar exceção para a camada de orquestração decidir retry/skip/abort (ticket "Failure-handling flow")?

## Answer

- **Fronteira de erro**: nunca propaga exceção crua — todo erro continua logado via `loguru` e vira um resultado com `status="error"`. Vocabulário de status é `Status = Literal["done", "error"]` (não o Command state completo — `skipped`/`cancelled` são decisões de orquestração, tomadas antes de sequer chamar `run_*`).
- **Um dataclass por comando** (`BootstrapResult`, `MeasureResult`, `ReportResult`, `ConsolidateResult`), sem base compartilhada — espelha o padrão já usado pelos `Request` (`MeasureRequest` etc. em `main.py`, também sem base comum). Cada um colocado no mesmo arquivo do seu `run_*` (não em `main.py`, que só importa).
- **`exit_code` não é campo armazenado** — deriva de `status` via um helper compartilhado (`exit_code_for(status: Status) -> int`), evitando duas fontes de verdade divergentes num dataclass congelado.
- **Identidade**: `competencia`/`orgao` viram campos nos resultados (exceto `ConsolidateResult`, que não tem `orgao` — `consolidate` é agnóstico de órgão por definição). Isso também alimenta o schema do run-state (ticket "Run orchestrator and resume").
- **`--orgao both` no `cli_main`**: o loop `_each_single_orgao` deixa de fazer `code |= run_measure(...)` e passa a coletar `list[MeasureResult]` (etc.); um helper compartilhado reduz a lista a um código de saída agregado (`1` se algum resultado tem `status="error"`, senão `0`).
- **`warnings: tuple[str, ...]`** — presente em todo resultado (vazio quando limpo) — captura estruturalmente o que hoje só ia para `logger.warning` (ex.: config de `CADASTROS` não carregado, histórico de glosa ilegível), sem duplicar a lógica de negócio relendo logs ou arquivos de saída.
- **`error_message: str | None`** — campo separado de `warnings`, só preenchido quando `status="error"`. `warnings` = "funcionou, mas com ressalva"; `error_message` = "o motivo específico da falha" — distinção que os tickets "Failure-handling flow" e "Completion summary and exit codes" precisam para não ter que adivinhar qual entrada da lista foi a fatal.
- **`MeasureResult` granularidade**: campo `indicators: tuple[IndicatorOutcome, ...]`, um por indicador (até 14), com `contractual_id`, `rom_path`, `summary_path`, `hard_failure: bool`, `error: str | None` — não só contagem agregada, porque os tickets de falha e de resumo final precisam nomear qual indicador falhou.
- Formas finais confirmadas:

```python
Status = Literal["done", "error"]

# measure.py
@dataclass(frozen=True, slots=True)
class IndicatorOutcome:
    contractual_id: str
    rom_path: Path
    summary_path: Path
    hard_failure: bool
    error: str | None

@dataclass(frozen=True, slots=True)
class MeasureResult:
    status: Status
    competencia: str
    orgao: str
    indicators: tuple[IndicatorOutcome, ...]
    warnings: tuple[str, ...]
    error_message: str | None

# bootstrap.py
@dataclass(frozen=True, slots=True)
class BootstrapResult:
    status: Status
    orgao: str
    capa_path: Path
    created: bool  # False = capa já existia
    warnings: tuple[str, ...]
    error_message: str | None

# report.py
@dataclass(frozen=True, slots=True)
class ReportResult:
    status: Status
    competencia: str
    orgao: str
    output_path: Path
    indicator_count: int
    warnings: tuple[str, ...]
    error_message: str | None

# consolidate.py
@dataclass(frozen=True, slots=True)
class ConsolidateResult:
    status: Status
    competencia: str  # sem orgao — consolidate é agnóstico de órgão
    output_path: Path
    decisions_preserved: int
    warnings: tuple[str, ...]
    error_message: str | None
```

Nos caminhos de erro precoce (ex.: capa ausente em `report.py:38`, antes de qualquer indicador/output existir), o resultado ainda é construído com `status="error"`, campos que não puderam ser computados recebem placeholders vazios/zero (`indicator_count=0` etc.), e `error_message` carrega a mensagem específica.
