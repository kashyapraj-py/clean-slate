from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from cleanslate.cli import app
from conftest import python_project

runner = CliRunner()


def test_cli_scan_and_dry_run_are_read_only(workspace: Path, data_dir: Path, monkeypatch):
    monkeypatch.setenv("CLEANSLATE_DATA_DIR", str(data_dir))
    project = python_project(workspace)
    cache = project / "__pycache__"
    cache.mkdir()
    (cache / "x.pyc").write_bytes(b"hello")
    scanned = runner.invoke(app, ["scan", str(workspace), "--json"])
    assert scanned.exit_code == 0, scanned.output
    assert '"python-bytecode"' in scanned.output
    dry_run = runner.invoke(app, ["clean", str(workspace)])
    assert dry_run.exit_code == 0, dry_run.output
    assert "Dry run only" in dry_run.output
    assert cache.exists()


def test_cli_apply_and_restore(workspace: Path, data_dir: Path, monkeypatch):
    monkeypatch.setenv("CLEANSLATE_DATA_DIR", str(data_dir))
    project = python_project(workspace)
    cache = project / "__pycache__"
    cache.mkdir()
    (cache / "x.pyc").write_bytes(b"hello")
    applied = runner.invoke(app, ["clean", str(workspace), "--apply", "--yes"])
    assert applied.exit_code == 0, applied.output
    assert not cache.exists()
    history_result = runner.invoke(app, ["history", "--json"])
    assert history_result.exit_code == 0, history_result.output
    history = json.loads(history_result.output)
    restored = runner.invoke(app, ["restore", history[0]["id"], "--yes"])
    assert restored.exit_code == 0, restored.output
    assert (cache / "x.pyc").read_bytes() == b"hello"
