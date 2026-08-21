import re
from pathlib import Path

import pytest

from pyauditor.orchestration.state import (
    CommandStateEntry,
    RunState,
    RunStateCorrupted,
    load_state,
    reset_stale_running,
    save_state,
    state_path,
)


def test_state_path_keys_on_competencia_and_orgao_selector() -> None:
    path = state_path("2026-06", "both", Path("/runs"))
    assert path == Path("/runs/2026-06-both.json")


def test_save_and_load_state_roundtrips(tmp_path: Path) -> None:
    path = state_path("2026-06", "MinC", tmp_path)
    state = RunState(
        competencia="2026-06",
        orgao_selector="MinC",
        commands=(
            CommandStateEntry(command="bootstrap", orgao="MinC", status="done"),
            CommandStateEntry(command="measure", orgao="MinC", status="pending"),
        ),
    )

    save_state(path, state)
    loaded = load_state(path)

    assert loaded == state


def test_load_state_returns_none_when_file_absent(tmp_path: Path) -> None:
    assert load_state(state_path("2026-06", "MinC", tmp_path)) is None


def test_load_state_raises_run_state_corrupted_on_malformed_json(tmp_path: Path) -> None:
    path = state_path("2026-06", "MinC", tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not json", encoding="utf-8")

    with pytest.raises(RunStateCorrupted, match=re.escape(str(path))):
        load_state(path)


def test_load_state_raises_run_state_corrupted_on_missing_key(tmp_path: Path) -> None:
    path = state_path("2026-06", "MinC", tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"competencia": "2026-06"}', encoding="utf-8")

    with pytest.raises(RunStateCorrupted):
        load_state(path)


def test_load_state_raises_run_state_corrupted_on_unknown_status(tmp_path: Path) -> None:
    path = state_path("2026-06", "MinC", tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '{"competencia": "2026-06", "orgao_selector": "MinC", "commands": '
        '[{"command": "bootstrap", "orgao": "MinC", "status": "not_a_real_status"}]}',
        encoding="utf-8",
    )

    with pytest.raises(RunStateCorrupted, match="not_a_real_status"):
        load_state(path)


def test_reset_stale_running_resets_only_running_entries() -> None:
    state = RunState(
        competencia="2026-06",
        orgao_selector="MinC",
        commands=(
            CommandStateEntry(command="bootstrap", orgao="MinC", status="done"),
            CommandStateEntry(command="measure", orgao="MinC", status="running", started_at="t"),
        ),
    )

    fixed = reset_stale_running(state)

    assert fixed.commands[0].status == "done"
    assert fixed.commands[1].status == "pending"
    assert fixed.commands[1].started_at is None
