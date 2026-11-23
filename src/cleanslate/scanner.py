"""Project discovery and conservative, explained cleanup recommendations."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

from .config import Settings, validate_root
from .git import GitInventory, inventory
from .inspect import signature
from .models import Candidate, Project, ScanResult, path_contains
from .rules import matching_rule

MARKERS: dict[str, frozenset[str]] = {
    "python": frozenset({
        "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile",
        "poetry.lock", "uv.lock", "tox.ini",
    }),
    "node": frozenset({"package.json"}),
    "rust": frozenset({"Cargo.toml"}),
    "php": frozenset({"composer.json"}),
}

# Never descend into private VCS internals or unrelated tool metadata.
SKIP_DISCOVERY = frozenset({
    ".git", ".hg", ".svn", ".idea", ".vscode", ".terraform", ".gradle",
    ".cache", ".cargo", ".npm", ".pnpm-store", "site-packages",
})


def _ecosystems(names: set[str]) -> tuple[str, ...]:
    return tuple(kind for kind, markers in MARKERS.items() if names.intersection(markers))


def _entries(folder: Path) -> list[os.DirEntry[str]]:
    with os.scandir(folder) as entries:
        return sorted(list(entries), key=lambda e: e.name.casefold())


def scan(workspace: Path, *, data_dir: Path | None = None, max_depth: int = 8) -> ScanResult:
    initial = workspace.expanduser().absolute()
    settings = Settings.load(initial, data_dir=data_dir, max_depth=max_depth)
    root = validate_root(initial, settings.data_dir)
    # After canonicalization, resolve workspace-level .cleanslate.toml consistently.
    settings = Settings.load(root, data_dir=settings.data_dir, max_depth=max_depth)
    report = ScanResult(root=str(root), scanned_at=datetime.now(timezone.utc).isoformat())
    git_cache: dict[Path, GitInventory] = {}
    visited: set[Path] = set()

    def walk(folder: Path, depth: int, current: Project | None) -> None:
        if settings.excluded(folder, root) or folder in visited:
            return
        visited.add(folder)
        try:
            children = _entries(folder)
        except OSError as exc:
            report.warnings.append(f"Cannot inspect {folder}: {exc}")
            return
        names = {entry.name for entry in children}
        tech = _ecosystems(names)
        if tech or ".git" in names:
            current = Project(str(folder), folder.name, tech or ("other",), ".git" in names)
            report.projects.append(current)
            git_cache[folder] = inventory(folder)
        if current is None:
            # Parent folder may contain many projects; keep searching up to depth limit.
            if depth >= settings.max_depth:
                return
        for entry in children:
            path = folder / entry.name
            if settings.excluded(path, root):
                continue
            try:
                if entry.is_symlink():
                    continue
                is_dir = entry.is_dir(follow_symlinks=False)
                is_file = entry.is_file(follow_symlinks=False)
            except OSError as exc:
                report.warnings.append(f"Cannot inspect {path}: {exc}")
                continue
            if entry.name in SKIP_DISCOVERY:
                continue
            if current is not None and (is_dir or is_file):
                rule = matching_rule(entry.name, is_dir, current.ecosystems, settings.disabled_rules)
                if rule is not None:
                    checked = signature(path)
                    git = git_cache[Path(current.path)]
                    protected = checked.protected_reason or git.error
                    if path_contains(settings.data_dir, path):
                        protected = "Contains Clean Slate's private data"
                    if git.protects(path):
                        protected = "Contains Git-tracked files"
                    candidate_id = hashlib.sha256(str(path).encode("utf-8", "surrogateescape")).hexdigest()[:20]
                    report.candidates.append(Candidate(
                        id=candidate_id,
                        path=str(path),
                        project_path=current.path,
                        name=rule.label,
                        rule_id=rule.id,
                        category=rule.category,
                        risk=rule.risk,
                        reason=rule.explanation,
                        bytes=checked.size,
                        files=checked.files,
                        fingerprint=checked.fingerprint,
                        protected_reason=protected,
                    ))
                    # Do not rescan inside recognized generated artifacts.
                    continue
            if is_dir and depth < settings.max_depth:
                walk(path, depth + 1, current)

    walk(root, 0, None)
    report.candidates.sort(key=lambda item: (-item.bytes, item.path))
    report.projects.sort(key=lambda item: item.path)
    return report
