# Week 16 Submission Evidence: Student Document Request Tracker

**Student**: Namoc, Charles Klyde T.  
**Course Milestone**: Week 16 — Hosting Evaluation & Test Environment Deployment  
**Project**: Student Document Request Tracker  
**Date**: 17 November 2026  
**Target Environment**: Windows 11, Flutter Web `3.47.7` (Release Bundle), FastAPI `uvicorn`, Nginx `1.30.4`, MySQL `8.4.3` (`sdrt_staging`), Microsoft Edge (Playwright)

---

## 1. Submission Package Contents

### Production Deployment Templates (`deploy/`)
| File | Description |
|---|---|
| **[../../deploy/nginx.conf](../../deploy/nginx.conf)** | Production Nginx reverse proxy with TLS 1.2/1.3, Flutter SPA fallback, `/api/` pass-through preserving API 404s, security headers, and dotfile denial. |
| **[../../deploy/sdrt-api.service](../../deploy/sdrt-api.service)** | `systemd` service unit for FastAPI (`uvicorn app.main:app`) with least-privileged user `sdrt` and hardened paths. |
| **[../../deploy/sdrt-scheduler.service](../../deploy/sdrt-scheduler.service)** | `systemd` service unit for the single designated APScheduler worker (`python -m app.automation.scheduler`) with `Restart=always`. |
| **[../../deploy/.env.production.example](../../deploy/.env.production.example)** | Secret-free production environment variable template. |
| **[../../deploy/backup.sh](../../deploy/backup.sh)** | Paired `mysqldump` + private uploads archive script with SHA-256 manifests and 7-day rolling retention. |
| **[../../deploy/README.md](../../deploy/README.md)** | Linux VPS provisioning checklist and disaster recovery runbook. |

### Week 16 Exit Evidence (`evidence/week16/`)
| File / Folder | Description |
|---|---|
| **[vps-evaluation.md](vps-evaluation.md)** | Hosting evaluation comparing Hostinger VPS, Oracle Cloud Always Free, AWS EC2 Free Tier, and GitHub Student Pack vs. incompatible PaaS/serverless tiers. |
| **[verification.md](verification.md)** | Full Week 16 verification report detailing test results, measured backup/restore durations, and staging observations. |
| **[verification/api-smoke-test-env.json](verification/api-smoke-test-env.json)** | 20-check release smoke test output executed through Nginx (`http://localhost:8080`). |
| **[verification/protected-download-check.json](verification/protected-download-check.json)** | 4-case authorization & SHA-256 integrity results for `/api/v1/files/{file_id}`. |
| **[verification/restore-verification.json](verification/restore-verification.json)** | Post-disaster restoration metrics (`backup_duration_seconds=0.667`, `restore_duration_seconds=3.51`, 24 tables, 22 triggers, 3/3 hashes). |
| **[logs/scheduler-restart.log](logs/scheduler-restart.log)** | Real stdout/stderr capture showing `GET_LOCK` duplicate rejection, abrupt process kill, and `lease_recovered` + `succeeded` retry. |
| **[logs/backup-restore.log](logs/backup-restore.log)** | Verbatim log of paired `mysqldump` + zip backup, destructive wipe simulation, restore, and post-restore smoke verification. |
| **[screenshots/](screenshots/)** | 6 visual proofs (`staging-app-nginx.png`, `protected-download-401.png`, `protected-download-200.png`, `scheduler-restart-recovery.png`, `mysql-backup-dump.png`, `mysql-restore-success.png`). |

---

## 2. Reproduction Steps

1. Start MySQL 8.4 with `log_bin_trust_function_creators = 1` and create `sdrt_staging` with privileges for `'sdrt'@'127.0.0.1'`.
2. Build the Flutter Web release bundle:
   ```powershell
   flutter build web --release --no-wasm-dry-run
   ```
3. Apply migrations and seed `sdrt_staging`, launch FastAPI on `127.0.0.1:8081` (`PYTHONPATH=backend`), and start Nginx on `127.0.0.1:8080` proxying `/api/` to `8081` and serving `build/web` at `/`.
4. Run the automated verification suite:
   ```powershell
   & backend/.venv/Scripts/python.exe scripts/week16_verify.py
   ```
5. Run regression suites:
   ```powershell
   flutter analyze
   flutter test
   $env:PYTHONPATH = 'backend'
   & backend/.venv/Scripts/python.exe -m pytest backend/tests backend/week14_tests
   ```
