# Instale o pyauditor

O `pyauditor` é um CLI em Python 3.12+ gerenciado por [uv](https://docs.astral.sh/uv/).

## Pré-requisitos

- Python 3.12 ou superior.
- [uv](https://docs.astral.sh/uv/) instalado.

## Procedimento

1. Clone o repositório e entre na raiz do projeto:

   ```bash
   git clone <url-do-repositorio>
   cd pyauditor
   ```

2. Sincronize as dependências (cria o ambiente virtual):

   ```bash
   uv sync
   ```

3. Verifique a instalação:

   ```bash
   uv run pyauditor --help
   ```

   A saída lista os subcomandos `bootstrap`, `measure` e `report`.

## Verificação

A presença dos três subcomandos na saída confirma a instalação. Se `uv sync`
falhar, verifique a versão do Python (`python --version`) e a presença do `uv`
antes de continuar.

## Próximos passos

- [Quickstart](quickstart.md) — rode sua primeira competência de ponta a ponta.