"""Read-only, size-first duplicate detection with bounded work."""

from __future__ import annotations

import hashlib
import os
from collections import defaultdict
from pathlib import Path

from .config import Settings, validate_root
from .models import CleanSlateError
from .scanner import SKIP_DISCOVERY


def find_duplicates(
    workspace: Path,
    *,
    data_dir: Path | None = None,
    max_files: int = 12_000,
    max_file_bytes: int = 512 * 1024 * 1024,
) -> dict:
    """Hash only equal-sized regular files; never follow symlinks or delete anything."""
    settings = Settings.load(workspace.expanduser().absolute(), data_dir=data_dir)
    root = validate_root(workspace, settings.data_dir)
    sizes: dict[int, list[Path]] = defaultdict(list)
    seen = 0
    skipped = 0
    for folder, dirs, files in os.walk(root, topdown=True, followlinks=False):
        parent = Path(folder)
        dirs[:] = sorted(
            dirname for dirname in dirs
            if dirname not in SKIP_DISCOVERY
            and dirname not in {"node_modules", ".venv", "venv", "target", "vendor"}
            and not (parent / dirname).is_symlink()
            and not settings.excluded(parent / dirname, root)
        )
        for name in sorted(files):
            candidate = parent / name
            if candidate.is_symlink() or settings.excluded(candidate, root):
                continue
            try:
                stat = candidate.stat(follow_symlinks=False)
            except OSError:
                skipped += 1
                continue
            if not candidate.is_file() or not 0 < stat.st_size <= max_file_bytes:
                skipped += 1
                continue
            seen += 1
            if seen > max_files:
                raise CleanSlateError(f"Duplicate scan limit ({max_files:,} files) reached. Narrow the root.")
            sizes[stat.st_size].append(candidate)
    hashes: dict[tuple[int, str], list[str]] = defaultdict(list)
    for size, paths in sizes.items():
        if len(paths) < 2:
            continue
        for path in paths:
            sha = hashlib.sha256()
            try:
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        sha.update(chunk)
                hashes[(size, sha.hexdigest())].append(str(path))
            except OSError:
                skipped += 1
    groups = [
        {"bytes_per_file": size, "reclaimable_bytes": size * (len(paths) - 1),
         "sha256": sha, "paths": sorted(paths)}
        for (size, sha), paths in hashes.items() if len(paths) > 1
    ]
    groups.sort(key=lambda group: -group["reclaimable_bytes"])
    return {
        "root": str(root), "files_scanned": seen, "files_skipped": skipped,
        "reclaimable_bytes": sum(group["reclaimable_bytes"] for group in groups),
        "groups": groups[:100], "truncated": len(groups) > 100,
        "notice": "Read-only report. No duplicate files are deleted automatically.",
    }
