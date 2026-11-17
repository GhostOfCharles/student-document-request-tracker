# Project Implementation Progress

**Last Updated**: 17 November 2026  
**Current Milestone**: Week 16 Complete (Ready for Week 17 User Acceptance & Rehearsal)  

---

## 1. Milestone Status Overview

| Milestone | Implementation Focus | Required Exit Evidence | Status |
|---|---|---|---|
| **Week 13** | Core workflow vertical slice, real MySQL constraints, dynamic requirement renderer, durable automation, retry failure recovery | Verified schema (23 tables, 22 triggers), passing pytest/Flutter suites, scheduler interruption recovery logs, browser screenshots | **COMPLETE** |
| **Week 14** | Student registration, service draft editor, publishing controls, availability toggles, profiles, temporary staff password forced resets | Wireframes mapped to implemented routes, version immutability verification, manager permissions test suite (`week14_tests`), isolated browser captures | **COMPLETE** |
| **Week 15** | Integration and usability testing; verify invalid transitions, uploads, retry races, responsive layouts, error handling; defect resolution | Test matrix (`evidence/week15/test-matrix.md`), defect register (`evidence/week15/defect-register.md`), passing suites, 7 visual demonstrations, updated docs | **COMPLETE** |
| **Week 16** | Evaluate VPS hosting against persistent Python, MySQL, private storage, HTTPS and scheduler requirements; test environment deployment | Deployment configs (`deploy/`), VPS evaluation (`evidence/week16/vps-evaluation.md`), staging smoke tests, scheduler restart logs, protected download tests, paired restore evidence | **COMPLETE** |
| **Week 17** | User acceptance with controlled evidence, help content refinement, complete demonstration and recovery rehearsal | Acceptance results, issue dispositions, final interface captures, reproducible demo procedure | *Upcoming* |
| **Week 18** | Freeze assessed release, finalize documentation, archive evidence, handover and presentation | Tagged GitHub release, migration inventory, final documentation, demonstration recording | *Scheduled* |

---

## 2. Week 16 Verification Checklist

| Criterion | Target | Verification Result | Evidence Reference |
|---|---|---|---|
| **VPS Hosting Evaluation** | Evaluate Hostinger VPS & free-tier VPS options vs. PaaS | **COMPLETE** | `evidence/week16/vps-evaluation.md` |
| **Deployment Configuration** | Production Nginx, systemd API/scheduler units, backup script | **COMPLETE** | `deploy/nginx.conf`, `deploy/sdrt-api.service`, `deploy/sdrt-scheduler.service`, `deploy/backup.sh` |
| **Release Build & Regression Suites** | 0 analyzer errors, all Flutter & pytest suites pass | **PASS** (17/17 Flutter, 19/19 Pytest) | `flutter analyze`, `flutter test`, `flutter build web --release`, `pytest backend/tests backend/week14_tests` |
| **Isolated Staging Smoke** | Reverse-proxied release build + API lifecycle pass | **PASS** (20/20) | `evidence/week16/verification/api-smoke-test-env.json`, `evidence/week16/screenshots/staging-app-nginx.png` |
| **Protected File Downloads** | Unauthenticated 401, cross-student 404, owner/staff 200 | **PASS** (4/4) | `evidence/week16/verification/protected-download-check.json`, `protected-download-401.png`, `protected-download-200.png` |
| **Scheduler Restart & Lease Recovery** | Single-lock enforcement, crash recovery, 0 duplicate notices | **PASS** | `evidence/week16/logs/scheduler-restart.log`, `evidence/week16/screenshots/scheduler-restart-recovery.png` |
| **Paired Backup & Restore** | Consistent dump + private uploads wipe & full restore | **PASS** (0.667s dump / 3.51s restore) | `evidence/week16/logs/backup-restore.log`, `restore-verification.json`, `mysql-backup-dump.png`, `mysql-restore-success.png` |

---

## 3. Week 15 Verification Checklist

| Criterion | Target | Verification Result | Evidence Reference |
|---|---|---|---|
| **Static Code Quality** | 0 errors, 0 warnings | **PASS** | `flutter analyze` completed with 0 issues |
| **Frontend Unit & Widget Tests** | All passing | **PASS** (17/17) | `flutter test` executed 17 test cases with 100% pass rate |
| **Backend Core Suite** | All passing | **PASS** (13/13) | `pytest backend/tests` (13 tests passed against MySQL) |
| **Backend Week 14/15 Suite** | All passing | **PASS** (6/6) | `pytest backend/week14_tests` (6 tests passed against MySQL test schema) |
| **Live API Smoke** | Zero regressions | **PASS** (9/9) | `scripts/api_smoke.py` -> `evidence/week15/verification/api-smoke.json` |
| **Browser Authentication Smoke** | Zero regressions | **PASS** (6/6) | `scripts/login_smoke.py` -> `evidence/week15/verification/student-ui-smoke.json` |
| **Staff Console Navigation** | Zero console errors | **PASS** (15/15) | `scripts/staff_design_smoke.py` -> `evidence/week15/verification/staff-visual-smoke.json` |
| **Request Review UX Redesign** | Modern 2-column layout, document cards, action priority | **VERIFIED** | `evidence/week15/screenshots/request-review-desktop.png` & `mobile.png` |
| **Multi-Viewport Ergonomics** | Desktop ($\ge 900\,\text{px}$) & Mobile ($390\,\text{px}$) | **VERIFIED** | 7 screenshots in `evidence/week15/screenshots/` and visual manifest |
| **Defect Tracking** | All discovered defects documented and resolved | **CLOSED** (8/8) | `evidence/week15/defect-register.md` |
| **Test Matrix** | Comprehensive coverage of state machine, RBAC, uploads, races | **DOCUMENTED** | `evidence/week15/test-matrix.md` |

---

## 4. Operational State at Handover

* **Local Backend Service**: FastAPI running on `http://localhost:8000` (dev) and verified behind Nginx `1.30.4` on `http://localhost:8080` -> `127.0.0.1:8081` (staging).
* **Database Service**: MySQL 8.4.3 (Laragon) running on port 3306 with schemas `sdrt` (dev seed), `sdrt_test` (disposable test schema), and `sdrt_staging` (isolated Week 16 staging schema).
* **Triggers & Immutability**: All 22 database triggers active and enforcing published version immutability.
* **Test Accounts**:
  * Student: `student@example.test` / `TEST-001`
  * Registrar Staff: `registrar@example.test` / `STAFF-TEST-001`
  * Service Manager: `registrar@example.test` (with `can_manage_services=True`)
