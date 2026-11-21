"""Filesystem snapshotting without symlink traversal or content reads."""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path

from .models import FileSignature

PROTECTED_FILES = {
    ".env", ".npmrc", ".pypirc", ".git", ".gitignore", ".gitmodules",
    "id_rsa", "id_ed25519", "credentials.json", "secrets.json",
}
PROTECTED_EXTENSIONS = {".db", ".sqlite", ".sqlite3", ".pem", ".key", ".p12", ".pfx"}


def sensitive_filename(name: str) -> bool:
    lower = name.lower()
    return (
        lower in PROTECTED_FILES
        or lower.startswith(".env.")
        or lower.startswith("id_rsa.")
        or lower.startswith("id_ed25519.")
        or Path(lower).suffix in PROTECTED_EXTENSIONS
    )


def signature(path: Path, *, max_items: int = 250_000) -> FileSignature:
    """Snapshot apparent size and names/stats. Mark suspicious contents protected.

    Uses lstat, never follows links, and fails closed when unreadable or too large.
    Changes to any traversed filename, metadata, or directory invalidate the hash.
    """
    digest = hashlib.sha256()
    stack = [path]
    size = 0
    files = 0
    nodes = 0
    protected: str | None = None
    while stack:
        current = stack.pop()
        nodes += 1
        if nodes > max_items:
            protected = protected or "Too many files to verify safely"
            break
        try:
            info = current.lstat()
        except OSError as exc:
            protected = protected or f"Unreadable item: {exc.strerror or exc}"
            break
        relative = current.relative_to(path).as_posix()
        digest.update(f"{relative}\0{info.st_mode}\0{info.st_size}\0{info.st_mtime_ns}\0".encode(
            "utf-8", errors="surrogateescape"
        ))
        if stat.S_ISLNK(info.st_mode):
            protected = protected or "Contains a symbolic link"
            continue
        if sensitive_filename(current.name):
            protected = protected or "Contains sensitive or configuration files"
        if stat.S_ISDIR(info.st_mode):
            try:
                with os.scandir(current) as entries:
                    children = sorted((Path(entry.path) for entry in entries), reverse=True)
                stack.extend(children)
            except OSError as exc:
                protected = protected or f"Unreadable directory: {exc.strerror or exc}"
        elif stat.S_ISREG(info.st_mode):
            size += info.st_size
            files += 1
        else:
            protected = protected or "Contains a non-regular filesystem item"
    return FileSignature(size, files, digest.hexdigest(), protected)
