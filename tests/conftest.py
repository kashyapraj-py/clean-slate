from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    return root


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    root = tmp_path / "private-data"
    root.mkdir(mode=0o700)
    return root


def python_project(root: Path, name: str = "demo") -> Path:
    project = root / name
    project.mkdir()
    (project / "pyproject.toml").write_text('[project]\nname = "demo"\n')
    return project
