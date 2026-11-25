# Contributing to Clean Slate

Clean Slate is intentionally cautious: a false positive in a cleanup tool is more serious than a missed cache. Contributions should preserve that principle.

## Local setup

1. Fork and clone the repository.
2. Use Python 3.11+ and install `python -m pip install -e ".[web,dev]"`.
3. Run `python -m pytest` before changing code.
4. For UI changes, run `cd frontend && npm install && npm run typecheck && npm run build`.
5. Keep changes focused and include a regression test for new behavior.

## Adding a cleanup rule

- Add it to `src/cleanslate/rules.py` with a clear explanation and ecosystem.
- Prefer `risk="review"` for new patterns. Never recommend a folder only because it has a common or vague name.
- Explain how users can reproduce the contents and how accidental local modifications are handled.
- Add a test proving ordinary generated files are recognized, plus a test proving sensitive and Git-tracked files remain protected.
- Do not add rules that remove databases, secrets, Git internals, source code, or unrelated user files.

## Python style

- Use type hints for public functions and simple, focused modules.
- Do not silently catch errors or guess that failed filesystem checks mean a file is safe.
- Keep the filesystem read-only until the user explicitly chooses and confirms a cleanup.
- Preserve compatibility with Python 3.11–3.13 and common Windows/macOS/Linux filesystems.

## UI style

- Keep commands accessible with readable labels, keyboard focus and clear loading/errors.
- Present exact paths, risks and sizes before any move.
- Keep user data on the local API; avoid analytics, hidden remote endpoints or unrequested uploads.

## Pull requests

Describe the problem, behavior change, safety implications, and tests. Screenshots are helpful for UI work. Report security-sensitive issues privately via GitHub security advisories instead of public issues.
