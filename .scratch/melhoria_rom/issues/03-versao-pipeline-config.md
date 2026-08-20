Type: research
Status: resolved

## Question

Como obter, de forma confiável, "versão do pipeline" e "versão da
configuração" para o ROM?

- Verificar se `importlib.metadata.version("pyauditor")` funciona no modo de
  instalação/execução atual deste projeto (checar `pyproject.toml`, se é
  instalado via `uv sync`/editable install, e se `pyauditor measure` roda a
  partir do pacote instalado ou direto do source tree via `uv run`).
- Se `importlib.metadata.version` puder lançar `PackageNotFoundError` nesse
  modo de execução, qual o fallback razoável (string fixa "dev", ou tentar
  `git rev-parse --short HEAD` se `.git` existir)?
- "Versão da configuração" = SHA-256 do arquivo YAML do indicador
  (`config_path`, já disponível em `discover_configs`/`load_config` —
  ver `engine/pipeline.py:32-34,75-96`) — confirmar que dá para computar o
  hash sem reabrir o arquivo (ele já foi lido como texto em
  `load_config`/`discover_configs`; decidir se o hash é calculado ali ou se
  vale reabrir o arquivo em bytes por simplicidade).

## Answer

**Versão do pipeline:** `importlib.metadata.version("pyauditor")` funciona hoje,
de forma confiável, e é o mecanismo primário a usar.

- `pyproject.toml` declara `[project] name = "pyauditor"` com `version = "0.1.0"`
  estática — não há `setuptools_scm`, `hatch-vcs` nem `dynamic = [...]`; o
  build backend é `uv_build` (não gera versão via git tags).
- O README confirma o fluxo de execução: `uv sync` (instala em modo editable
  no `.venv/`) seguido de `uv run pyauditor <subcomando> ...`. Ou seja, mesmo
  rodando a partir do source tree, o pacote está registrado no ambiente via
  editable install — os metadados ficam disponíveis para `importlib.metadata`.
- Testado diretamente: `.venv/bin/python -c "import importlib.metadata;
  print(importlib.metadata.version('pyauditor'))"` retornou `0.1.0` sem
  exceção. Portanto no modo de execução atual deste projeto (`uv sync` +
  `uv run pyauditor ...`) `importlib.metadata.version("pyauditor")` é
  confiável e não lança `PackageNotFoundError`.
- Fallback (para o caso hipotético de rodar sem instalação, ex.: script solto
  fora de `uv run`/`.venv`, ou pacote não instalado): capturar
  `importlib.metadata.PackageNotFoundError` e cair para
  `git rev-parse --short HEAD` (o repo tem `.git`; `git rev-parse
  --is-inside-work-tree` confirma), e se `git` também falhar (tarball sem
  `.git`, ambiente sem git), usar a string fixa `"dev"` como último recurso.
  Recomenda-se compor a string final como algo como `f"{version} ({commit})"`
  quando ambos estiverem disponíveis, para rastreabilidade extra, mas o campo
  mínimo exigido é só a versão do `importlib.metadata`.

**Versão da configuração (hash do YAML):**

- Em `engine/pipeline.py`, tanto `load_config` (linha 33) quanto
  `discover_configs` (linha 84) já leem o YAML via
  `config_path.read_text(encoding="utf-8")`, mas hoje o texto lido é passado
  diretamente para `yaml.safe_load(...)` sem ser guardado numa variável — ou
  seja, não há como computar o hash "de graça" sem uma pequena mudança no
  código: basta atribuir o resultado de `read_text` a uma variável local
  (`raw_text = config_path.read_text(encoding="utf-8")`) antes de chamar
  `yaml.safe_load(raw_text)`, e então calcular
  `hashlib.sha256(raw_text.encode("utf-8")).hexdigest()` sobre esse mesmo
  texto — sem reabrir o arquivo em modo binário separadamente. Isso evita um
  segundo I/O e garante que o hash reflete exatamente os bytes que foram
  parseados.
- Hoje `IndicatorConfig` (`config/models.py:333`) não guarda `config_path` nem
  hash — `MeasurementResult` (pipeline.py:17-21) só carrega o `IndicatorConfig`
  já validado, então o hash computado em `load_config`/`discover_configs`
  precisa ser propagado explicitamente (ex.: como campo adicional em
  `IndicatorConfig`/`MeasurementResult`, ou retornado junto do config como
  tupla/dataclass) para chegar até `rom/render.py:render_rom`, que hoje só
  recebe `MeasurementResult` e não tem acesso ao path/hash da config.
- Reabrir o arquivo em modo binário separadamente (`config_path.read_bytes()`)
  é desnecessário e menos seguro (risco de a leitura textual e a leitura
  binária não coincidirem, ex. mudanças de encoding/normalização de EOL entre
  as duas chamadas); a abordagem recomendada é hashear o mesmo `raw_text`
  (`.encode("utf-8")`) já lido para o `yaml.safe_load`.
