# Local HTTP API

Base URL: `http://127.0.0.1:8765`. Browser dashboard development uses Vite on `http://127.0.0.1:5173` with a proxy. Every mutation requires `Content-Type: application/json` and a trusted `Origin` header when a browser sends one.

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Version and ready status |
| GET | `/api/meta` | Default workspace, data directory, safety message |
| GET | `/api/rules` | Built-in cleanup policy |
| POST | `/api/scans` | Scan workspace and issue one-use receipt |
| POST | `/api/cleanups` | Move selected candidates to quarantine |
| GET | `/api/history` | Most recent operations with item details |
| POST | `/api/restores` | Restore remaining items of an operation |
| POST | `/api/duplicates` | Bounded, read-only duplicate analysis |

## Example scan

```bash
curl -X POST http://127.0.0.1:8765/api/scans \
  -H 'Content-Type: application/json' \
  -d '{"root":"/home/user/Projects","max_depth":8}'
```

Response contains `scan_id`, `root`, `projects`, `candidates`, `warnings`, `safe_bytes`, `total_bytes`, `protected_count`, `scanned_at`. Candidate fields include `id`, `rule_id`, `risk`, `reason`, `bytes`, `files`, `path`, `fingerprint`, `protected_reason`, `can_clean`.

## Apply selected candidates

```json
{
  "scan_id": "receipt-from-previous-scan",
  "candidate_ids": ["selected-candidate-id"],
  "confirm_review": false
}
```

POST to `/api/cleanups`. Receipts expire after 20 minutes, are single-use, and are discarded even if validation fails. `confirm_review: true` is mandatory if **any** selected item is review-risk. The service verifies the snapshot again before moving anything.

Cleanup responses contain `operation`, `moved_count`, `errors`. For a partial cleanup, inspect `errors` and the history before repeating operations.

## Recovery

```json
{"operation_id":"operation-id-from-history"}
```

POST to `/api/restores`. It restores only remaining items and refuses to overwrite existing destinations. A partial result includes an `errors` array, allowing the user to resolve path conflicts and retry.

## Duplicates

```json
{"root":"/home/user/Projects"}
```

POST to `/api/duplicates`. Returns `groups` of `{sha256, paths, bytes_per_file, reclaimable_bytes}`. No duplicate file deletion endpoint exists.

FastAPI also provides the local OpenAPI explorer at `/docs` while the API is running.
