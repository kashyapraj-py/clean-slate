"""Read-only Git awareness: tracked files are protected even when ignored elsewhere."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class GitInventory:
    root: Path | None
    tracked: frozenset[Path]
    error: str | None = None

    def protects(self, candidate: Path) -> bool:
        return any(path == candidate or candidate in path.parents for path in self.tracked)


def inventory(project_dir: Path) -> GitInventory:
    try:
        result = subprocess.run(
            ["git", "-C", str(project_dir), "rev-parse", "--show-toplevel"],
            capture_output=True, timeout=6, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return GitInventory(None, frozenset(), f"Cannot verify Git safety: {exc}")
    if result.returncode != 0:
        # Git can fail for unsafe ownership, missing permissions, or damaged repos.
        # If a .git marker exists in the ancestry, fail closed rather than
        # misclassifying a broken repository as ordinary untracked files.
        if any(((ancestor / ".git").exists() or (ancestor / ".git").is_symlink()) for ancestor in
               (project_dir, *project_dir.parents)):
            return GitInventory(None, frozenset(), "Cannot verify Git repository safety")
        return GitInventory(None, frozenset())
    root: Path | None = None
    try:
        root = Path(result.stdout.decode("utf-8", errors="surrogateescape").strip()).resolve()
        tracked_result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "-z"],
            capture_output=True, timeout=12, check=False,
        )
        if tracked_result.returncode != 0:
            raise OSError(tracked_result.stderr.decode(errors="replace").strip())
        tracked = frozenset(
            root / name.decode("utf-8", errors="surrogateescape")
            for name in tracked_result.stdout.split(b"\0") if name
        )
        return GitInventory(root, tracked)
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        return GitInventory(root, frozenset(),
                            f"Cannot verify Git safety: {exc}")
