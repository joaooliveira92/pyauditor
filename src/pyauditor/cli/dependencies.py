"""Thin registry mapping each Command to its precondition checker (ticket
"Dependency enforcement", .scratch/interactive-cli map). The checking logic
itself lives colocated in each command's own file — this module only wires
them together so dispatch (`cli_main`, the orchestrator, the interactive
layer) has one place to look a Command's checker up.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

from pyauditor.cli.bootstrap import check_bootstrap_ready
from pyauditor.cli.consolidate import check_consolidate_ready
from pyauditor.cli.measure import check_measure_ready
from pyauditor.cli.report import check_report_ready
from pyauditor.cli.results import DependencyCheck

CHECKERS: Final[dict[str, Callable[..., DependencyCheck]]] = {
    "bootstrap": check_bootstrap_ready,
    "measure": check_measure_ready,
    "report": check_report_ready,
    "consolidate": check_consolidate_ready,
}
