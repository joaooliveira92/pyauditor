"""pyauditor — top-level package. Re-exports the `project.scripts` entry
point; the implementation lives in `cli/main.py` alongside `cli_main`."""

from pyauditor.cli.main import main

__all__ = ('main',)
