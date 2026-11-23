"""Conservative built-in rules. Review artifacts always require explicit approval."""

from .models import Rule

RULES: tuple[Rule, ...] = (
    Rule("python-bytecode", "Python bytecode", "cache", frozenset({"python"}),
         folder_names=frozenset({"__pycache__"}), risk="safe",
         explanation="CPython recreates bytecode from source when needed."),
    Rule("python-pyc", "Python bytecode files", "cache", frozenset({"python"}),
         file_names=frozenset({".pyc", ".pyo"}), risk="safe",
         explanation="Compiled Python modules can be regenerated."),
    Rule("pytest-cache", "pytest cache", "cache", frozenset({"python"}),
         folder_names=frozenset({".pytest_cache"}), risk="safe",
         explanation="pytest regenerates its run metadata."),
    Rule("mypy-cache", "mypy cache", "cache", frozenset({"python"}),
         folder_names=frozenset({".mypy_cache"}), risk="safe",
         explanation="mypy regenerates type-checking cache files."),
    Rule("ruff-cache", "Ruff cache", "cache", frozenset({"python"}),
         folder_names=frozenset({".ruff_cache"}), risk="safe",
         explanation="Ruff regenerates lint cache files."),
    Rule("python-venv", "Python virtual environment", "dependencies", frozenset({"python"}),
         folder_names=frozenset({".venv", "venv"}), risk="review",
         explanation="Environment removal can require reinstalling packages or restoring local edits."),
    Rule("tox-envs", "tox / nox environments", "dependencies", frozenset({"python"}),
         folder_names=frozenset({".tox", ".nox"}), risk="review",
         explanation="Test environments may contain tools or dependencies that are expensive to recreate."),
    Rule("node-modules", "Node dependencies", "dependencies", frozenset({"node"}),
         folder_names=frozenset({"node_modules"}), risk="review",
         explanation="Dependencies can be reinstalled, but local patches or generated assets may be lost."),
    Rule("node-cache", "Node tool caches", "cache", frozenset({"node"}),
         folder_names=frozenset({".turbo", ".vite", ".parcel-cache"}), risk="safe",
         explanation="Tool-generated caches can be rebuilt."),
    Rule("next-output", "Next.js output", "build", frozenset({"node"}),
         folder_names=frozenset({".next", ".nuxt", ".svelte-kit"}), risk="review",
         explanation="Framework output should be reviewed before removal."),
    Rule("build-output", "Build / distribution output", "build", frozenset({"python", "node"}),
         folder_names=frozenset({"build", "dist"}), risk="review",
         explanation="Build directories may contain distributable or manually added files."),
    Rule("rust-target", "Rust compilation output", "build", frozenset({"rust"}),
         folder_names=frozenset({"target"}), risk="review",
         explanation="Rust rebuilds output, but this can require substantial time."),
    Rule("composer-vendor", "Composer dependencies", "dependencies", frozenset({"php"}),
         folder_names=frozenset({"vendor"}), risk="review",
         explanation="Installed PHP packages may include uncommitted patches."),
)


def matching_rule(name: str, is_dir: bool, ecosystems: tuple[str, ...], disabled: frozenset[str]) -> Rule | None:
    for rule in RULES:
        if rule.id in disabled or not rule.ecosystems.intersection(ecosystems):
            continue
        if is_dir and name in rule.folder_names:
            return rule
        if not is_dir and (name in rule.file_names or (
            rule.id == "python-pyc" and name.endswith((".pyc", ".pyo"))
        )):
            return rule
    return None
