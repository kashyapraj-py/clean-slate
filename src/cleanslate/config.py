"""Configuration and safety boundaries for local workspace operations."""

from __future__ import annotations

import fnmatch
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_dir

from .models import CleanSlateError, path_contains


@dataclass(frozen=True, slots=True)
class Settings:
    data_dir: Path
    exclude: tuple[str, ...] = ()
    disabled_rules: frozenset[str] = frozenset()
    max_depth: int = 8

    @classmethod
    def load(cls, workspace: Path, data_dir: Path | None = None, max_depth: int = 8) -> Settings:
        if not 0 <= max_depth <= 30:
            raise CleanSlateError("Scan depth must be between 0 and 30.")
        actual_data = data_dir or Path(
            os.environ.get("CLEANSLATE_DATA_DIR", user_data_dir("cleanslate", "Kashyap Raj"))
        )
        actual_data = actual_data.expanduser().resolve()
        configuration = workspace / ".cleanslate.toml"
        if not configuration.exists():
            return cls(data_dir=actual_data, max_depth=max_depth)
        try:
            with configuration.open("rb") as handle:
                data = tomllib.load(handle)
            section = data.get("scan", {})
            exclusions = section.get("exclude", [])
            disabled = section.get("disable_rules", [])
            if not isinstance(exclusions, list) or not all(isinstance(x, str) for x in exclusions):
                raise ValueError("scan.exclude must be an array of strings")
            if not isinstance(disabled, list) or not all(isinstance(x, str) for x in disabled):
                raise ValueError("scan.disable_rules must be an array of strings")
        except (OSError, ValueError) as exc:
            raise CleanSlateError(f"Invalid .cleanslate.toml: {exc}") from exc
        return cls(actual_data, tuple(exclusions), frozenset(disabled), max_depth)

    def excluded(self, path: Path, root: Path) -> bool:
        # Never scan Clean Slate's own quarantine even when the workspace is ~.
        if path_contains(path, self.data_dir):
            return True
        relative = path.relative_to(root).as_posix()
        for pattern in self.exclude:
            normalized = pattern.strip().strip("/")
            if normalized and (
                fnmatch.fnmatchcase(relative, normalized)
                or fnmatch.fnmatchcase(path.name, normalized)
                or relative == normalized
                or relative.startswith(normalized + "/")
                or (normalized.endswith("/**") and fnmatch.fnmatchcase(relative, normalized[:-3]))
            ):
                return True
        return False


def validate_root(path: Path, data_dir: Path | None = None) -> Path:
    """Only operate on existing physical directories, not symlinked workspace roots."""
    path = path.expanduser().absolute()
    if path.is_symlink():
        raise CleanSlateError("The workspace root must not be a symlink.")
    try:
        canonical = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise CleanSlateError(f"Cannot access workspace: {exc}") from exc
    if not canonical.is_dir():
        raise CleanSlateError("The workspace must be a directory.")
    if data_dir and path_contains(canonical, data_dir.resolve()):
        raise CleanSlateError("Scanning Clean Slate's private data or quarantine is disabled.")
    return canonical
