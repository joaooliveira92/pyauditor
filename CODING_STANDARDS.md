# Padrões de código — pyauditor

Referência usada pela skill `code-review` (eixo Standards) e por qualquer
agente que escreva ou revise código Python neste repositório. Baseado em
[python-production-engineer][ppe], adaptado ao stack real do projeto.

**Estilo de código Python** é delegado ao [pyguide.md][pyguide] (Google
Python Style Guide): seções 2 ("Python Language Rules") e 3 ("Python Style
Rules"). Este documento só registra as decisões específicas deste projeto e
as divergências conscientes.

## Stack e ferramentas obrigatórias

-   Python 3.12+, gerenciado via `uv` (`uv sync --group dev`, `uv run ...`).
    Não usar `pip install` direto para dependências do projeto.
-   `pyproject.toml` é a fonte única de configuração de lint, tipagem,
    testes e cobertura.
-   Lint/format: **Ruff** (`E`, `F`, `I`, `B`, `UP`, `SIM`, `RUF`). Corrigir
    o achado, não suprimir com `# noqa` sem justificativa localizada.
-   Tipagem: **mypy strict** (`[tool.mypy] strict = true`). Nenhum código
    novo deve introduzir `Any` evitável ou `# type: ignore` sem comentário
    explicando o motivo.
-   Testes: **pytest**, com `--cov` e `fail_under = 85`
    (`[tool.coverage.report]`). Rodar `uv run pytest` antes de declarar
    qualquer tarefa concluída.
-   Logging: **loguru** (`pyauditor.logging`). Nunca `print` em código de
    produção — só é aceitável em saída deliberada de CLI (Rich/questionary)
    voltada ao usuário final.
-   Validação/config: **pydantic** para schemas externos (YAML de
    configuração, manifestos); `dataclass(frozen=True, slots=True)` para
    tipos de domínio internos imutáveis — é o padrão já usado em
    `config/models.py`, `config/manifest.py`, `config/catalog.py`.
-   Caminhos: sempre `pathlib.Path`, nunca strings concatenadas.

## Estilo e nomes

Regras de estilo seguem o [pyguide.md][pyguide]. Divergências e decisões
específicas deste projeto:

-   Nomes em código (variáveis, funções, classes) em **inglês**, seguindo
    PEP 8 e o [pyguide.md][pyguide]. Comentários, docstrings, mensagens de
    erro e logs voltados ao usuário são em **pt-BR** (ver
    [CLAUDE.md][claude] — o usuário só lê pt-BR).
-   Comentários explicam o *porquê*, não repetem o código. Preferir nenhum
    comentário a um comentário óbvio.
-   Quando o [pyguide.md][pyguide] deixar margem de escolha (ex.:
    `# noqa` vs. reestruturar o código), a ferramenta configurada em
    [pyproject.toml][pyproject] (Ruff, mypy) é o árbitro.

## Erros e resiliência

-   Nunca engolir exceção silenciosamente (`except Exception: pass`). Toda
    captura ampla precisa adicionar contexto, logar e re-lançar ou converter
    para um outcome explícito — ver o padrão de `IndicatorOutcome` em
    `cli/measure.py`, que isola a falha de um indicador sem abortar o lote.
-   Usar `raise ... from exc` para preservar a causa.
-   Distinguir explicitamente: falha real (`hard_failure=True`,
    aborta/reporta erro) vs. estado esperado sem dado (ex.: dataset ausente
    na competência — não é falha, é "não ativado", conforme spec §14.1).
-   Mensagens de erro devem ser acionáveis: o quê falhou, onde, e — quando
    fizer sentido — o que fazer a respeito (ver `WRITE_FAILURE_HINT` em
    `cli/measure.py` como exemplo).
-   Nunca capturar `Exception` amplo perto do I/O de arquivo — capturar
    `OSError`/`ValueError` especificamente, e reservar `except Exception` só
    para isolar falha de um item dentro de um lote (documentar isso no
    comentário, como já feito).

## Testes

-   Um teste por comportamento, não por linha de código. Cobrir: caminho
    feliz, entrada inválida, e os estados de erro que o código distingue
    explicitamente (ex.: `hard_failure` vs. `not_activated` vs. sucesso).
-   Testes determinísticos: sem dependência de relógio real, ordem de
    filesystem ou rede.
-   Para bugs: escrever primeiro o teste que reproduz a falha, depois
    corrigir.
-   Não perseguir cobertura por número isolado — os 85% do gate existem
    para não regredir, não como meta a maximizar com testes triviais.

## Segurança

-   Nunca secrets, tokens ou credenciais em código, fixtures ou logs.
-   Entradas externas (YAML de config, CSV de dados, XLSX) são não
    confiáveis — validar na borda (pydantic para YAML; `defusedxml`/openpyxl
    com cautela para planilhas).
-   Sem `shell=True` em subprocess.

## Compatibilidade e mudanças

-   Não quebrar contratos de CLI (flags, formato de saída, exit codes)
    sem necessidade explícita.
-   Mudança mínima e coerente: não introduzir abstração nova sem um segundo
    caso de uso real já existente no código, essa é uma sugestão não uma
    hard-rule.
-   Extensões futuras: registrar como TODO/ticket, não implementar
    especulativamente.

## Antes de declarar uma tarefa concluída

1.  `uv run ruff check .`
2.  `uv run ruff format --check .` (ou aplicar formatação, se apropriado)
3.  `uv run mypy`
4.  `uv run pytest`

Nunca reportar sucesso sem ter rodado esses comandos. Se algum não puder
rodar, dizer exatamente qual, por quê, e o risco residual.

## Veja também

-   [pyguide.md][pyguide] — Google Python Style Guide.
-   [CLAUDE.md][claude] — convenções de comunicação e idioma do repositório.
-   [python-production-engineer](/agents/skills/python-production-engineer/SKILL.md) — skill base deste documento.
-   [pyproject.toml](pyproject.toml) — configuração de lint, tipagem e testes.

