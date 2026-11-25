# Security policy

Clean Slate is a **local filesystem tool** with the same operating-system permissions as the account running it. It is not safe to expose its API to untrusted networks or users.

## Reporting vulnerabilities

Please use the repository's private **Report a vulnerability** / GitHub Security Advisory feature when available. Avoid sharing proof-of-concept payloads that delete or move user files in a public issue before a fix can be prepared.

## Threat model

- The web service binds to loopback and validates browser request origins. There is no authentication for remote access. Never change the listen address to `0.0.0.0` on a reachable server.
- Git-tracked files, symlinks, sensitive filenames, filesystem special items, and unreadable directories are denied by default.
- Cache snapshots are verified again before moving files. This minimizes but cannot eliminate race conditions with concurrently running builds or malicious local programs.
- Recovery is local and persistent. The journal and quarantine require normal operating-system filesystem protections.
- Do not run Clean Slate as root or administrator except when you fully trust all scanned content and accept the elevated impact of mistakes.

## Supported versions

Security fixes target the current main branch and the latest tagged release. Older releases may not receive backports.
