from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from cleanslate.models import CleanSlateError
from cleanslate.scanner import scan
from conftest import python_project


def test_detects_projects_and_recognized_artifacts(workspace: Path, data_dir: Path):
    python = python_project(workspace)
    cache = python / "__pycache__"
    cache.mkdir()
    (cache / "index.cpython-313.pyc").write_bytes(b"ABC")
    venv = python / ".venv"
    venv.mkdir()
    (venv / "bin").mkdir()
    (venv / "bin" / "python").write_bytes(b"python")
    frontend = workspace / "web"
    frontend.mkdir()
    (frontend / "package.json").write_text('{"name":"web"}')
    (frontend / "node_modules").mkdir()
    (frontend / "node_modules" / "package.js").write_text("installed")
    rust = workspace / "rust"
    rust.mkdir()
    (rust / "Cargo.toml").write_text('[package]\nname="rust"')
    (rust / "target").mkdir()
    (rust / "target" / "app").write_bytes(b"APP")
    result = scan(workspace, data_dir=data_dir)
    assert len(result.projects) == 3
    by_rule = {c.rule_id: c for c in result.candidates}
    assert by_rule["python-bytecode"].risk == "safe"
    assert by_rule["python-bytecode"].bytes == 3
    assert by_rule["python-venv"].risk == "review"
    assert by_rule["node-modules"].risk == "review"
    assert by_rule["rust-target"].risk == "review"
    assert result.to_dict()["total_bytes"] == 3 + 6 + 9 + 3


def test_protects_sensitive_files_and_symlinks(workspace: Path, data_dir: Path):
    project = python_project(workspace)
    dist = project / "dist"
    dist.mkdir()
    (dist / "artifact.txt").write_text("present")
    (dist / ".env").write_text("secret=value")
    cache = project / "__pycache__"
    cache.mkdir()
    (cache / "cache.pyc").write_text("safe")
    try:
        (cache / "external").symlink_to(project, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks unavailable on this platform")
    result = scan(workspace, data_dir=data_dir)
    by_rule = {c.rule_id: c for c in result.candidates}
    assert by_rule["build-output"].protected_reason == "Contains sensitive or configuration files"
    assert by_rule["python-bytecode"].protected_reason == "Contains a symbolic link"


def test_git_tracked_files_are_protected(workspace: Path, data_dir: Path):
    project = python_project(workspace)
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    cache = project / "__pycache__"
    cache.mkdir()
    (cache / "tracked.pyc").write_bytes(b"important")
    subprocess.run(["git", "-C", str(project), "add", "--", "__pycache__/tracked.pyc"], check=True)
    result = scan(workspace, data_dir=data_dir)
    candidate = next(c for c in result.candidates if c.rule_id == "python-bytecode")
    assert candidate.protected_reason == "Contains Git-tracked files"


def test_config_excludes_directories_and_rules(workspace: Path, data_dir: Path):
    project = python_project(workspace)
    (project / "__pycache__").mkdir()
    (project / ".pytest_cache").mkdir()
    (workspace / ".cleanslate.toml").write_text('''
[scan]
exclude = ["demo/.pytest_cache"]
disable_rules = ["python-bytecode"]
''')
    result = scan(workspace, data_dir=data_dir)
    assert not result.candidates


def test_does_not_scan_quarantine(workspace: Path, data_dir: Path):
    nested_data_dir = workspace / "cleanslate-private"
    project = python_project(workspace)
    (project / "__pycache__").mkdir()
    nested_data_dir.mkdir()
    private_project = python_project(nested_data_dir, "not-a-project")
    (private_project / "__pycache__").mkdir()
    result = scan(workspace, data_dir=nested_data_dir)
    assert len(result.projects) == 1
    assert len(result.candidates) == 1


def test_rejects_invalid_or_symlink_roots(workspace: Path, data_dir: Path):
    with pytest.raises(CleanSlateError):
        scan(workspace / "missing", data_dir=data_dir)
    shortcut = workspace.parent / "shortcut"
    try:
        shortcut.symlink_to(workspace, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks unavailable")
    with pytest.raises(CleanSlateError):
        scan(shortcut, data_dir=data_dir)


def test_empty_workspace_does_not_error(workspace: Path, data_dir: Path):
    result = scan(workspace, data_dir=data_dir)
    assert result.projects == []
    assert result.candidates == []
    assert result.warnings == []


def test_never_offers_directory_containing_private_storage(workspace: Path):
    project = python_project(workspace)
    candidate_dir = project / "__pycache__"
    candidate_dir.mkdir()
    (candidate_dir / "cache.pyc").write_bytes(b"cache")
    private_dir = candidate_dir / "private"
    private_dir.mkdir()
    result = scan(workspace, data_dir=private_dir)
    match = next(item for item in result.candidates if item.rule_id == "python-bytecode")
    assert match.protected_reason == "Contains Clean Slate's private data"
