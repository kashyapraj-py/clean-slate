"""Destructive operations live here, behind explicit approval and fresh verification."""

from __future__ import annotations

import os
import shutil
import threading
import uuid
from pathlib import Path

from .config import validate_root
from .git import inventory
from .inspect import signature
from .models import Candidate, CleanSlateError, ScanResult, path_contains
from .storage import Journal


class CleanupService:
    """Moves selected verified candidates into a private, locally stored quarantine."""

    def __init__(self, data_dir: Path):
        self.journal = Journal(data_dir)
        self.data_dir = self.journal.data_dir
        self.lock = threading.RLock()

    def _validate(self, root: Path, candidate: Candidate) -> None:
        source = Path(candidate.path)
        project = Path(candidate.project_path)
        if not path_contains(source, root) or not path_contains(source, project):
            raise CleanSlateError("Selected path is outside its scanned workspace or project.")
        if path_contains(self.data_dir, source):
            raise CleanSlateError("Selected candidate contains Clean Slate's private data")
        if source.is_symlink() or not source.exists():
            raise CleanSlateError(f"Missing or symlinked candidate: {source}")
        if candidate.protected_reason:
            raise CleanSlateError(f"Protected item cannot be cleaned: {source}")
        snapshot = signature(source)
        if snapshot.protected_reason or snapshot.fingerprint != candidate.fingerprint:
            raise CleanSlateError(f"Files changed or became unsafe since scanning: {source}")
        git = inventory(project)
        if git.error or git.protects(source):
            raise CleanSlateError(f"Git protection prevents cleanup: {source}")
        # Block parent directory symlink substitutions between scan and application.
        _verify_parents(source, root)

    def cleanup(
        self, result: ScanResult, ids: list[str], *, confirm_review: bool = False,
    ) -> dict:
        if not ids or len(ids) != len(set(ids)):
            raise CleanSlateError("Select at least one unique candidate.")
        with self.lock:
            root = validate_root(Path(result.root), self.data_dir)
            possible = {item.id: item for item in result.candidates}
            if not set(ids).issubset(possible):
                raise CleanSlateError("Invalid candidate selection. Run a new scan.")
            selected = [possible[item_id] for item_id in ids]
            if any(c.risk == "review" for c in selected) and not confirm_review:
                raise CleanSlateError("Review-risk items require explicit additional approval.")
            # Verify ALL selected items before moving the first one.
            for item in selected:
                self._validate(root, item)
            op_id = uuid.uuid4().hex
            self.journal.start(op_id, str(root))
            moved = []
            errors = []
            quarantine_dir = self.data_dir / "quarantine" / op_id
            try:
                quarantine_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
            except OSError as exc:
                self.journal.finish(op_id, "failed")
                raise CleanSlateError(f"Could not create private quarantine directory: {exc}") from exc
            for candidate in selected:
                source = Path(candidate.path)
                target = quarantine_dir / candidate.id
                try:
                    # Recheck immediately before moving. A stale scan cannot be applied.
                    self._validate(root, candidate)
                    shutil.move(str(source), str(target))
                    try:
                        self.journal.record_item(op_id, candidate.id, source, target,
                                                 candidate.category, candidate.bytes)
                    except Exception:
                        # Never silently orphan files if the journal write fails.
                        shutil.move(str(target), str(source))
                        raise
                    moved.append(candidate.id)
                except Exception as exc:
                    errors.append(f"{source}: {exc}")
                    break
            status = "completed" if not errors else "partial" if moved else "failed"
            self.journal.finish(op_id, status)
            return {
                "operation": self.journal.operation(op_id),
                "moved_count": len(moved), "errors": errors,
            }

    def restore(self, operation_id: str) -> dict:
        with self.lock:
            operation = self.journal.operation(operation_id)
            root = validate_root(Path(operation["root"]), self.data_dir)
            restored = []
            errors = []
            for item in operation["items"]:
                if item["restored_at"]:
                    continue
                source = Path(item["quarantine_path"])
                destination = Path(item["original_path"])
                try:
                    if not path_contains(destination, root):
                        raise CleanSlateError("Destination is outside the original workspace")
                    _verify_parents(destination, root)
                    if os.path.lexists(destination):
                        raise CleanSlateError("Destination exists; refusing to overwrite it")
                    if not path_contains(source, self.data_dir / "quarantine"):
                        raise CleanSlateError("Invalid quarantine location")
                    if source.is_symlink() or not source.exists():
                        raise CleanSlateError("Quarantined item is missing or unsafe")
                    shutil.move(str(source), str(destination))
                    try:
                        self.journal.mark_restored(operation_id, item["id"])
                    except Exception:
                        shutil.move(str(destination), str(source))
                        raise
                    restored.append(item["id"])
                except Exception as exc:
                    errors.append(f"{destination}: {exc}")
            if not restored and not errors:
                raise CleanSlateError("No unrestored items in this operation.")
            return {
                "operation": self.journal.operation(operation_id),
                "restored_count": len(restored), "errors": errors,
            }


def _verify_parents(path: Path, root: Path) -> None:
    """Require all parent directories to exist as physical (non-symlink) dirs."""
    if not path_contains(path, root):
        raise CleanSlateError("Path is outside workspace")
    current = root
    if current.is_symlink() or not current.is_dir():
        raise CleanSlateError("Workspace directory is missing or symlinked")
    for name in path.relative_to(root).parts[:-1]:
        current = current / name
        if current.is_symlink() or not current.is_dir():
            raise CleanSlateError(f"Destination parent is missing or symlinked: {current}")
