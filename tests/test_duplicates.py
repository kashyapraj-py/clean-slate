from __future__ import annotations

from pathlib import Path

import pytest

from cleanslate.duplicates import find_duplicates
from cleanslate.models import CleanSlateError


def test_duplicates_find_same_content_not_just_same_name(workspace: Path, data_dir: Path):
    (workspace / "one.txt").write_text("matching")
    (workspace / "another.txt").write_text("matching")
    (workspace / "different.txt").write_text("different")
    result = find_duplicates(workspace, data_dir=data_dir)
    assert result["files_scanned"] == 3
    assert len(result["groups"]) == 1
    assert result["groups"][0]["reclaimable_bytes"] == len("matching")
    assert (workspace / "one.txt").is_file()  # Read-only guarantee.


def test_duplicates_avoid_dependencies_and_symlinks(workspace: Path, data_dir: Path):
    modules = workspace / "node_modules"
    modules.mkdir()
    (modules / "a.txt").write_text("matching")
    (modules / "b.txt").write_text("matching")
    (workspace / "a.txt").write_text("distinct")
    result = find_duplicates(workspace, data_dir=data_dir)
    assert result["groups"] == []


def test_duplicates_max_files(workspace: Path, data_dir: Path):
    for i in range(5):
        (workspace / f"{i}.txt").write_text("hello")
    with pytest.raises(CleanSlateError, match="limit"):
        find_duplicates(workspace, data_dir=data_dir, max_files=2)
