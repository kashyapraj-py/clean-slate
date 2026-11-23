"""Small, dependency-free domain models shared by the CLI and local API."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

Risk = Literal["safe", "review"]


@dataclass(frozen=True, slots=True)
class Rule:
    id: str
    label: str
    category: str
    ecosystems: frozenset[str]
    folder_names: frozenset[str] = frozenset()
    file_names: frozenset[str] = frozenset()
    risk: Risk = "review"
    explanation: str = ""


@dataclass(frozen=True, slots=True)
class Project:
    path: str
    name: str
    ecosystems: tuple[str, ...]
    git_repository: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Candidate:
    id: str
    path: str
    project_path: str
    name: str
    rule_id: str
    category: str
    risk: Risk
    reason: str
    bytes: int
    files: int
    fingerprint: str
    protected_reason: str | None = None

    @property
    def can_clean(self) -> bool:
        return self.protected_reason is None

    def to_dict(self) -> dict:
        return {**asdict(self), "can_clean": self.can_clean}


@dataclass(slots=True)
class ScanResult:
    root: str
    projects: list[Project] = field(default_factory=list)
    candidates: list[Candidate] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    scanned_at: str = ""

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "scanned_at": self.scanned_at,
            "projects": [item.to_dict() for item in self.projects],
            "candidates": [item.to_dict() for item in self.candidates],
            "warnings": self.warnings,
            "total_bytes": sum(c.bytes for c in self.candidates if c.can_clean),
            "safe_bytes": sum(c.bytes for c in self.candidates if c.can_clean and c.risk == "safe"),
            "protected_count": sum(not c.can_clean for c in self.candidates),
        }


@dataclass(frozen=True, slots=True)
class FileSignature:
    size: int
    files: int
    fingerprint: str
    protected_reason: str | None


class CleanSlateError(Exception):
    """An expected, user-actionable error in a Clean Slate operation."""


def path_contains(path: Path, parent: Path) -> bool:
    """Check containment on canonical paths; do not use string-prefix comparisons."""
    return path == parent or parent in path.parents
