from pathlib import Path

import pytest

from pyauditor.atomic_write import atomic_write


def test_atomic_write_creates_the_file_with_the_written_content(tmp_path: Path) -> None:
    path = tmp_path / "out.txt"

    atomic_write(path, lambda p: p.write_text("hello", encoding="utf-8"))

    assert path.read_text(encoding="utf-8") == "hello"


def test_atomic_write_creates_parent_directories(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "dir" / "out.txt"

    atomic_write(path, lambda p: p.write_text("hello", encoding="utf-8"))

    assert path.read_text(encoding="utf-8") == "hello"


def test_atomic_write_leaves_the_existing_file_untouched_on_failure(tmp_path: Path) -> None:
    path = tmp_path / "out.txt"
    path.write_text("original", encoding="utf-8")

    def _boom(_: Path) -> None:
        raise ValueError("simulated crash mid-write")

    with pytest.raises(ValueError, match="simulated crash"):
        atomic_write(path, _boom)

    assert path.read_text(encoding="utf-8") == "original"


def test_atomic_write_leaves_no_temp_file_behind_on_failure(tmp_path: Path) -> None:
    path = tmp_path / "out.txt"

    def _boom(_: Path) -> None:
        raise ValueError("simulated crash mid-write")

    with pytest.raises(ValueError):
        atomic_write(path, _boom)

    assert list(tmp_path.iterdir()) == []


def test_atomic_write_leaves_no_temp_file_behind_on_success(tmp_path: Path) -> None:
    path = tmp_path / "out.txt"

    atomic_write(path, lambda p: p.write_text("hello", encoding="utf-8"))

    assert list(tmp_path.iterdir()) == [path]
