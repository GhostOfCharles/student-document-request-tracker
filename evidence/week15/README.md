# Week 15 Submission Evidence: Student Document Request Tracker

**Student**: Namoc, Charles Klyde T.  
**Course Milestone**: Week 15 — Integration, Usability Testing & Defect Resolution  
**Project**: Student Document Request Tracker  
**Date**: 15 November 2026  
**Target Environment**: Windows 11, Flutter Web 3.47.7 (Dart 3.13.5), FastAPI 1.0.0, MySQL 8.4.3 (Laragon), Microsoft Edge (Playwright)

---

## 1. Submission Package Contents

This folder contains the complete verified evidence package for the Week 15 milestone:

| File / Folder | Description |
|---|---|
| **[verification.md](verification.md)** | Comprehensive Week 15 Verification and Integration Testing Report. Details system architecture, test suite outcomes, visual inspections, and exit criteria compliance. |
| **[test-matrix.md](test-matrix.md)** | Full 24-point Test Matrix exercising State Machine transitions, RBAC enforcement, File Upload security, Concurrency/Race conditions, Usability, and Error Handling. |
| **[defect-register.md](defect-register.md)** | Formal Defect Register recording all 8 identified defects (DEF-001 through DEF-008), root causes, engineering fixes, and verification evidence. All 8 closed. |
| **[how-to-run.txt](how-to-run.txt)** | Step-by-step instructions to run the FastAPI backend, background scheduler, and Flutter Web frontend in local development. |
| **[screenshots/](screenshots/)** | 7 high-resolution UI captures across Desktop ($1440 \times 950$) and Mobile ($390 \times 844$) viewports demonstrating responsive layouts and usability redesigns. |
| **[verification/](verification/)** | Machine-readable JSON test logs from live API smoke tests, visual smoke checks, and Playwright browser executions. |

---

## 2. Test Execution & Verification Summary

All test suites and automated checks pass with a 100% success rate:

| Test Suite / Tool | Scope | Status | Result |
|---|---|:---:|---|
| `flutter analyze` | Static code analysis across all frontend Dart code | **PASS** | 0 errors, 0 warnings across all files |
| `flutter test` | Flutter widget, layout, and state machine tests | **PASS** | 17 / 17 tests passed |
| `pytest backend/tests` | Core backend integration, file staging, and trigger security | **PASS** | 13 / 13 tests passed |
| `pytest backend/week14_tests` | Service management and account permissions | **PASS** | 6 / 6 tests passed |
| `scripts/api_smoke.py` | Live REST API endpoint smoke suite | **PASS** | 9 / 9 checks passed |
| `scripts/login_smoke.py` | Browser authentication and navigation smoke | **PASS** | 6 / 6 checks passed |
| `scripts/staff_design_smoke.py` | Multi-viewport console inspection | **PASS** | 15 / 15 viewport checks passed |
| `scripts/visual_review.py` | Fixture-based responsive UI test suite | **PASS** | 46 browser views verified without overflow |

---

## 3. Visual Verification Artifacts (`screenshots/`)

1. **`request-review-desktop.png`**: Desktop ($1440\,\text{px}$) 2-column split layout with requirements, document cards, and action priority.
2. **`request-review-mobile.png`**: Mobile ($390\,\text{px}$) stacked layout with priority action panel.
3. **`service-management-desktop.png`**: Registrar service management console with draft editor and availability controls.
4. **`staff-dashboard-desktop.png`**: Registrar dashboard with operational metrics, pending queue, and aging alerts.
5. **`student-dashboard-desktop.png`**: Student dashboard with active requests and document service catalog.
6. **`student-request-detail-desktop.png`**: Student request detail view with immutable timeline and milestone stepper.
7. **`student-request-detail-mobile.png`**: Student request detail view rendered in narrow mobile viewport.

---

## 4. Controlled Test Credentials

All seed accounts use the password configured in `.env` (`@7B!bP1Pzd*RAXy8#4ItSz@p`):
* **Student 1**: `TEST-001` (`student@example.test`)
* **Student 2**: `TEST-002` (`other@example.test`)
* **Registrar Staff**: `STAFF-TEST-001` (`registrar@example.test`)
