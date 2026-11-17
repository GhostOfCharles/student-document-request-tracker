# Week 16 Deployment Preparation & Staging Verification Report

**Date**: 17 November 2026  
**Student**: Namoc, Charles Klyde T.  
**Base Commit**: `3b1c4f4`  
**Schema Revision**: `0002_published_children` (24 tables incl. `alembic_version`, 22 immutability triggers)  
**Target Staging Environment**: Windows 11, Flutter Web `3.47.7` (release bundle `build/web`), Python `3.14.8` (FastAPI `uvicorn` on `127.0.0.1:8081`), Nginx `1.30.4` (`127.0.0.1:8080`), MySQL `8.4.3` (`sdrt_staging`), Microsoft Edge (Playwright)

---

## 1. Milestone Scope & Exit Criteria

In accordance with `docs/implementation-progress.md` and Section 13 of `docs/specification/project-extracted.txt` (*Deployment and operational handover*), Week 16 verifies:

1. **VPS Hosting Evaluation**: Candidate providers (Hostinger KVM 1, Oracle Cloud Always Free, AWS EC2 Free Tier, GitHub Student Developer Pack) evaluated against persistent Python, dedicated APScheduler lock, MySQL 8.4 triggers, private filesystem storage, and HTTPS reverse proxy (`vps-evaluation.md`).
2. **Production Deployment Configuration**: Complete Linux `nginx.conf`, `systemd` units (`sdrt-api.service`, `sdrt-scheduler.service`), secret-free `.env.production.example`, paired `backup.sh`, and operations runbook (`deploy/`).
3. **Isolated Staging Deployment & Release Smoke**: Compiled `flutter build web --release` served via Nginx reverse proxy at `http://localhost:8080` against isolated MySQL schema `sdrt_staging` and private directory `.private/staging_uploads`.
4. **Dedicated Scheduler Restart & Lease Recovery**: Verified MySQL `GET_LOCK('sdrt_designated_scheduler', 0)` blocks duplicate instances, then forcefully killed (`SIGKILL`/terminate) and restarted the scheduler to confirm `WORKER_INTERRUPTED` run marking, abandoned lease recovery, and zero duplicate notifications.
5. **Protected File Downloads**: Verified `/api/v1/files/{file_id}` through Nginx enforces `401` when unauthenticated, `404` on cross-student isolation (`TEST-002` requesting `TEST-001`'s file), and `200` with `Cache-Control: private, no-store`, `Content-Security-Policy: sandbox; default-src 'none'`, and verified SHA-256 checksums for authorized owner and staff sessions.
6. **Paired Backup & Restore Rehearsal**: Executed `mysqldump --single-transaction --routines --triggers --hex-blob` paired with `.private/staging_uploads` archive, simulated complete database & storage wipe, restored both artifacts, and verified all 24 tables, 22 triggers, 2 requests (`SDRT-2026-000001`, `SDRT-2026-000002`), and 3/3 file SHA-256 hashes.

---

## 2. Verification Matrix

| Check / Suite | Scope | Result | Measured Output & Evidence |
|---|---|---|---|
| `flutter analyze` | Static Dart analysis across frontend | **PASS** | 0 issues found (`73.8s`) |
| `flutter test` | Frontend widget & state tests | **PASS** | `17 / 17` tests passed |
| `flutter build web --release` | Production static web bundle | **PASS** | Compiled `build/web` (`88.8s`) |
| `pytest backend/tests backend/week14_tests` | Backend core, acceptance edges, Week 14–15 suites | **PASS** | `19 / 19` tests passed against `sdrt_test` (`36.31s`) |
| Staging Release Smoke (`scripts/week16_verify.py`) | Nginx routing, SPA fallback, `/api/v1/*` 404, full request lifecycle (`submitted` -> `completed`), RBAC | **PASS** | `20 / 20` checks passed (`verification/api-smoke-test-env.json`, `screenshots/staging-app-nginx.png`) |
| Protected Download Verification | `/api/v1/files/3` unauthenticated `401`, cross-student `404`, owner & staff `200` + SHA-256 | **PASS** | `4 / 4` cases passed (`verification/protected-download-check.json`, `screenshots/protected-download-401.png`, `screenshots/protected-download-200.png`) |
| Scheduler Restart & Lease Recovery | Duplicate `GET_LOCK` guard, abrupt kill (`pid=3328`), restart (`pid=13548`), `WORKER_INTERRUPTED` + retry | **PASS** | Job `11` recovered (`['interrupted', 'succeeded']`), `1` notification (`logs/scheduler-restart.log`, `screenshots/scheduler-restart-recovery.png`) |
| Paired Backup & Restore Rehearsal | `mysqldump` + uploads zip -> full wipe -> restore -> SHA-256 & UI check | **PASS** | Backup `0.667s`, Restore `3.51s`, `24` tables, `22` triggers, `3/3` hashes (`logs/backup-restore.log`, `verification/restore-verification.json`, `screenshots/mysql-backup-dump.png`, `screenshots/mysql-restore-success.png`) |

---

## 3. Infrastructure Defect Caught & Fixed During Staging

During initial Nginx staging header verification, `curl`/`Invoke-WebRequest` against `/` showed that `X-Content-Type-Options: nosniff` and `X-Frame-Options: SAMEORIGIN` were missing on static routes even though they were declared at the `server {}` block level. Because Nginx suppresses inherited `add_header` directives whenever a child `location` block defines its own `add_header` (such as `Cache-Control`), both `deploy/nginx.conf` and the local staging Nginx config were updated to declare all security headers inside the static and SPA `location` blocks, then reloaded and re-verified (`ROOT=200 X-Content-Type=nosniff X-Frame=SAMEORIGIN`).
