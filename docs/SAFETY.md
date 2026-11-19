# Cleanup safety and limitations

## Safe does not mean disposable in every workflow

Clean Slate distinguishes **safe** (known regenerated tool caches) from **review** (dependency environments, build output and similar potentially valuable directories). Neither category implies you are required to delete anything. A marked-safe cache can still be useful for expensive offline builds; review each cleanup in context.

## Blocking conditions

- Candidate path is a symlink, or the candidate contains any symlink.
- Any file is a sensitive filename (`.env*`, credentials, signing keys, PEM/PFX files, SQLite/database extensions, Git metadata and known user secrets).
- Git reports a tracked file anywhere inside the selected path.
- A file is unreadable, a non-regular filesystem object or a snapshot exceeds the inspection safety cap.
- Snapshot metadata no longer matches what was scanned, or a directory parent has become a symlink.
- The destination is no longer inside the scan root, or the scan root is missing.
- An item was marked review but the caller did not separately approve review-risk cleanup.

## What quarantine guarantees

- The original path is not immediately destroyed, but moved to a per-operation private directory.
- SQLite maintains a durable mapping of original path to recovered storage path.
- Restore never overwrites an existing destination. Users can move conflicting files out of the way and retry.
- A move across filesystems may perform a copy followed by removal; it may require free space and is not atomic.
- A crash or power loss in a filesystem move or before journaling can leave incomplete state. Check both the original and quarantine directories before repeating a failed operation.
- Recovery depends on the private data directory remaining intact. It is not a backup solution.

## Concurrency caveat

File metadata fingerprints are a practical change detector, not an unbreakable race-free proof. Do not run cleanup at the same time as compilers, package installers, code generators or adversarial processes modifying the same directories. No software that moves files using ordinary filesystem APIs can guarantee complete protection from all concurrent modifications without stronger OS-level facilities.

## Known exclusions

Project discovery does not enter VCS internals, common editor metadata and recognized generated artifacts. It searches down to eight directory levels by default. Duplicate scanning deliberately skips dependency directories and enforces work limits.

## Web server boundary

The web API is unauthenticated for local use and binds only to `127.0.0.1`. It restricts browser origins and accepts JSON-only state-changing requests. Do not publicly expose the API via tunnels, reverse proxies, Docker network bindings or remote-forwarded ports. The application can read or move any *eligible* file accessible to the logged-in user under the path they scan.
