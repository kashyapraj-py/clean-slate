from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from cleanslate.models import CleanSlateError
from cleanslate.scanner import scan
from cleanslate.service import CleanupService
from conftest import python_project


def _setup(workspace: Path, data_dir: Path, folder: str = "__pycache__"):
    project = python_project(workspace)
    candidate_dir = project / folder
    candidate_dir.mkdir()
    (candidate_dir / "file.txt").write_text("temporary bytes")
    return candidate_dir, scan(workspace, data_dir=data_dir), CleanupService(data_dir)


def test_cleanup_moves_and_restore_recovers_files(workspace: Path, data_dir: Path):
    original, report, service = _setup(workspace, data_dir)
    chosen = report.candidates[0]
    result = service.cleanup(report, [chosen.id])
    op = result["operation"]
    assert op["status"] == "completed"
    assert result["moved_count"] == 1
    assert not original.exists()
    assert (data_dir / "quarantine" / op["id"] / chosen.id / "file.txt").is_file()
    assert len(service.journal.history()) == 1
    fresh_service = CleanupService(data_dir)
    restored = fresh_service.restore(op["id"])
    assert restored["restored_count"] == 1
    assert (original / "file.txt").read_text() == "temporary bytes"
    assert fresh_service.journal.operation(op["id"])["restored_count"] == 1
    with pytest.raises(CleanSlateError, match="No unrestored"):
        fresh_service.restore(op["id"])


def test_review_requires_explicit_confirmation(workspace: Path, data_dir: Path):
    original, report, service = _setup(workspace, data_dir, "dist")
    with pytest.raises(CleanSlateError, match="additional approval"):
        service.cleanup(report, [report.candidates[0].id])
    assert original.is_dir()
    result = service.cleanup(report, [report.candidates[0].id], confirm_review=True)
    assert result["moved_count"] == 1


def test_stale_scan_refuses_changed_data(workspace: Path, data_dir: Path):
    original, report, service = _setup(workspace, data_dir)
    (original / "second.pyc").write_text("new")
    with pytest.raises(CleanSlateError, match="changed"):
        service.cleanup(report, [report.candidates[0].id])
    assert (original / "second.pyc").exists()
    assert service.journal.history() == []


def test_restore_never_overwrites_existing_destination(workspace: Path, data_dir: Path):
    original, report, service = _setup(workspace, data_dir)
    result = service.cleanup(report, [report.candidates[0].id])
    original.mkdir()
    (original / "replacement.txt").write_text("not to be overwritten")
    restored = service.restore(result["operation"]["id"])
    assert restored["restored_count"] == 0
    assert "refusing to overwrite" in restored["errors"][0]
    assert (original / "replacement.txt").read_text() == "not to be overwritten"
    (original / "replacement.txt").unlink()
    original.rmdir()
    restored = service.restore(result["operation"]["id"])
    assert restored["restored_count"] == 1


def test_protected_item_cannot_be_selected(workspace: Path, data_dir: Path):
    project = python_project(workspace)
    dist = project / "dist"
    dist.mkdir()
    (dist / ".env").write_text("secret")
    report = scan(workspace, data_dir=data_dir)
    service = CleanupService(data_dir)
    assert report.candidates[0].protected_reason
    with pytest.raises(CleanSlateError, match="Protected"):
        service.cleanup(report, [report.candidates[0].id], confirm_review=True)
    assert dist.exists()


def test_invalid_selections_rejected(workspace: Path, data_dir: Path):
    original, report, service = _setup(workspace, data_dir)
    with pytest.raises(CleanSlateError):
        service.cleanup(report, [])
    with pytest.raises(CleanSlateError):
        service.cleanup(report, [report.candidates[0].id, report.candidates[0].id])
    with pytest.raises(CleanSlateError):
        service.cleanup(report, ["invented-candidate"])
    assert original.exists()


def test_newly_tracked_file_after_scan_blocks_cleanup(workspace: Path, data_dir: Path):
    project = python_project(workspace)
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    cache = project / "__pycache__"
    cache.mkdir()
    (cache / "temporary.pyc").write_bytes(b"to-preserve")
    report = scan(workspace, data_dir=data_dir)
    assert report.candidates[0].can_clean
    subprocess.run(["git", "-C", str(project), "add", "-f", "--", "__pycache__/temporary.pyc"], check=True)
    with pytest.raises(CleanSlateError, match="Git protection"):
        CleanupService(data_dir).cleanup(report, [report.candidates[0].id])
    assert cache.is_dir()


def test_restore_refuses_symlinked_parent(workspace: Path, data_dir: Path):
    original, report, service = _setup(workspace, data_dir)
    operation_id = service.cleanup(report, [report.candidates[0].id])["operation"]["id"]
    project = original.parent
    elsewhere = workspace / "elsewhere"
    elsewhere.mkdir()
    shutil.rmtree(project)
    try:
        project.symlink_to(elsewhere, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks unavailable")
    result = service.restore(operation_id)
    assert result["restored_count"] == 0
    assert "symlinked" in result["errors"][0]
    assert not (elsewhere / "__pycache__").exists()
