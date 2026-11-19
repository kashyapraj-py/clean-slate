# Architecture

Clean Slate is a local program with two independent interfaces sharing one Python core.

```text
Typer CLI ─────┐
               ├── scanner → rules → snapshot + Git inventory
FastAPI API ───┤
               └── cleanup service → quarantine + SQLite journal
React frontend ───HTTP JSON──► FastAPI API
```

## Read path

`scanner.scan()` validates a workspace root, discovers manifest-bearing project directories, applies TOML exclusions, matches conservative generated-artifact rules, performs `lstat`-based snapshots, and consults Git's cached index. It returns `Project` and `Candidate` dataclasses. Neither scanning nor duplicate detection changes project files.

`duplicates.find_duplicates()` walks regular files while avoiding common dependency directories, groups by size, computes SHA-256 only for potentially matching files, and returns at most 100 groups. It never suggests automatically removing duplicates.

## Write path

`CleanupService.cleanup()` validates all selected candidates, rechecks snapshots and Git status, creates one operation ID, moves items into a private quarantine path, and records each move in SQLite. It returns the operation and any errors; a partial operation can be restored in its entirety later.

`CleanupService.restore()` reads durable operation records. For each unrestored item it requires the original parent directories to be physical directories and refuses to overwrite an occupied path. Restoration is individually recorded in the journal.

## API interaction

`POST /api/scans` produces a random, 20-minute, one-use scan receipt. The web API only accepts candidate IDs already bound to that server-generated receipt; callers cannot submit their own filesystem paths as cleanup targets. Source snapshots are checked again immediately before applying the plan. `ScanSessions` is intentionally in-memory; restarting the API invalidates pending plans but does not affect recovery records.

## Persistence

`platformdirs` chooses an OS-appropriate local data directory unless `CLEANSLATE_DATA_DIR` overrides it. The SQLite schema contains `operations` and `items`; each item records the original and quarantine paths, category, byte count and restore time. The database stores metadata, not file contents.

## Frontend

Vite proxies `/api` in development; the built React app can be served by the same FastAPI process after `npm run build`. Navigation is state-driven, and each write requires user interaction. A cleanup modal explicitly handles review-risk items.

## Extending the project

Keep adapters (CLI/API/frontend) unaware of OS-specific filesystem details. Add new rules only through the policy module. Add regression tests whenever a code change affects a path's eligibility, a recovery guarantee, a request boundary or a persistent record.
