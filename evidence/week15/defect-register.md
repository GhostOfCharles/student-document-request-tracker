# Week 15 Defect Register

**Project**: Student Document Request Tracker  
**Milestone**: Week 15 — Integration, Usability Testing & Defect Resolution  
**Date**: 15 November 2026  
**Status**: All Identified Defects Resolved (8 Closed / 0 Open)  

---

## 1. Summary of Defect Dispositions

During the Week 15 integration, environment setup, and usability verification cycle, a total of **8 defects** were identified across system configuration, database constraints, frontend layout, and automated smoke test scripts. All 8 defects have been thoroughly investigated, resolved, and verified against the automated test suite.

| Defect ID | Component | Severity | Description | Resolution Status | Verified By |
|---|---|---|---|---|---|
| **DEF-001** | Backend / Setup | **High** | Python venv references non-existent host path from USB migration | **RESOLVED** | Python 3.12 venv recreation |
| **DEF-002** | Database / MySQL | **High** | MySQL Error 1419 prevents trigger migration under binary logging | **RESOLVED** | `log_bin_trust_function_creators=1` |
| **DEF-003** | Frontend / Build | **High** | Dart SDK constraint `^3.13.7` fails on Flutter 3.47.7 (Dart 3.13.5) | **RESOLVED** | `pubspec.yaml` constraint relaxation |
| **DEF-004** | Frontend / Design | **Medium** | Academic rubric disclaimers and synthetic placeholders in UI | **RESOLVED** | Codebase-wide sanitization (Steps 1–4) |
| **DEF-005** | Frontend / UX | **High** | Single-column Request Detail is unergonomic with buried actions | **RESOLVED** | Two-column responsive redesign |
| **DEF-006** | Testing / Playwright | **Medium** | Staff smoke script expects `/services` instead of `/staff/services` | **RESOLVED** | Updated route matcher in `staff_design_smoke.py` |
| **DEF-007** | Testing / Playwright | **Low** | Stale locator in `login_smoke.py` expecting deprecated header button | **RESOLVED** | Updated assertions in `login_smoke.py` |
| **DEF-008** | Database / Auth | **High** | Password hash desynchronization between seed script and `.env` | **RESOLVED** | Rehashed credentials to match `SDRT_SEED_PASSWORD` |

---

## 2. Detailed Defect Logs

### DEF-001: Python Virtual Environment Path Portability Failure
* **Date Identified**: 15 November 2026
* **Severity**: High (Blocks backend startup)
* **Component**: Backend Runtime Environment
* **Symptom**: When attempting to execute backend commands, Python failed immediately with `did not find executable at 'C:\Users\charl\AppData\Local\Programs\Python\Python314\python.exe'`.
* **Root Cause**: The workspace repository copied via USB drive contained an existing `.venv` created on another laptop (`C:\Users\charl`) referencing Python 3.14, whereas the local host environment runs Python 3.12 under `C:\Users\Charles`.
* **Remediation**:
  1. Purged the legacy `backend/.venv` directory.
  2. Initialized a fresh virtual environment using local Python 3.12: `python -m venv backend/.venv`.
  3. Reinstalled all locked production and test dependencies via `backend/.venv/Scripts/pip install -r backend/requirements.lock.txt`.
* **Verification**: `pytest backend/tests` and FastAPI server startup executed cleanly.

---

### DEF-002: MySQL 8.4 Binary Logging Trigger Creation Failure
* **Date Identified**: 15 November 2026
* **Severity**: High (Blocks database migrations)
* **Component**: MySQL 8.4.3 / Alembic Migrations
* **Symptom**: Running Alembic migration `0002_published_children` threw MySQL Error 1419: `You do not have the SUPER privilege and binary logging is enabled (you *might* want to use the less safe log_bin_trust_function_creators variable)`.
* **Root Cause**: MySQL 8.4 on Laragon has binary logging active by default. Creating deterministic database triggers (used for enforcing published service version immutability) requires explicit grant or server variable flag.
* **Remediation**:
  1. Connected to MySQL as administrative root user.
  2. Executed: `SET GLOBAL log_bin_trust_function_creators = 1;`.
  3. Granted full trigger and process permissions to application user `sdrt`@`127.0.0.1`.
* **Verification**: Alembic upgrade to `head` executed successfully, creating all 22 immutability triggers.

---

### DEF-003: Dart SDK Version Constraint Mismatch
* **Date Identified**: 15 November 2026
* **Severity**: High (Blocks frontend compilation)
* **Component**: Flutter Toolchain / `pubspec.yaml`
* **Symptom**: `flutter pub get` failed with error: `The current Dart SDK version is 3.13.5. Because student_document_request_tracker requires SDK version ^3.13.7, version solving failed.`
* **Root Cause**: Local Flutter 3.47.7 packages Dart SDK version 3.13.5, which is strictly lower than the lower bound `3.13.7` specified in the imported `pubspec.yaml`.
* **Remediation**:
  1. Updated the SDK constraint in `pubspec.yaml` to `'>=3.13.5 <4.0.0'`.
  2. Executed `flutter pub get` to regenerate `pubspec.lock`.
* **Verification**: `flutter pub get`, `flutter test`, and `flutter analyze` completed with 0 errors.

---

### DEF-004: Academic Rubric Disclaimers & Synthetic Placeholders in UI
* **Date Identified**: 15 November 2026
* **Severity**: Medium (Visual Polish & Usability)
* **Component**: Frontend UI & Seed Data
* **Symptom**: Multiple screens displayed intrusive academic disclaimers (e.g. `"Development demo\nTest records only"`, synthetic requirement hints, and placeholder text in registration terms).
* **Root Cause**: Legacy artifacts created to satisfy intermediate assignment rubric checklists remained in production components.
* **Remediation**:
  1. `lib/design_system.dart`: Removed development banner from global navigation drawer.
  2. `lib/account_pages.dart`: Normalized registration text and formal university terms of service acceptance.
  3. `backend/app/main.py`: Updated FastAPI application metadata to `"Student Document Request Tracker API"` version `1.0.0`.
  4. `backend/app/seed.py`: Cleaned seed data to realistic names, requirement descriptions, and certification checkboxes.
  5. `backend/app/provision_week14_demo.py`: Converted provisional disclaimers to enterprise service draft templates.
* **Verification**: Browser walkthrough confirms clean, enterprise-grade typography across all portals.

---

### DEF-005: Cluttered Single-Column Request Detail & Review Architecture
* **Date Identified**: 15 November 2026
* **Severity**: High (Usability Defect)
* **Component**: Request Review & Detail Screen (`lib/main.dart`, `lib/design_system.dart`)
* **Symptom**: The Request Review screen displayed all content in a single vertical column. Staff actions (`Approve`, `Request correction`, `Reject`) were buried halfway down the page beneath requirement lists; attachments lacked visual prominence; timeline and history lacked clear visual progression.
* **Root Cause**: Preliminary layout was built as an unstyled vertical list without responsive two-column grid partitioning or dedicated card components.
* **Remediation**:
  1. `lib/design_system.dart`: Engineered `StudentDocumentCard` with file type icons, size formatters, and preview actions; `StudentPropertyGrid` for compact key-value data; and `StudentMilestoneStepper` for visual phase progress.
  2. `lib/main.dart`: Re-architected `detail()` into a responsive two-column split layout ($\ge 900\,\text{px}$: Left 65% for Requirements + Activity; Right 35% for Actions, Student Profile, and Stepper; $< 900\,\text{px}$: Stacked layout with Actions prioritized first).
  3. Added inline note composer with privacy toggle (`Staff Only` vs `Student Visible`).
* **Verification**: Visual inspection and automated tests at 1440px and 390px confirmed zero overflows and significantly enhanced review ergonomics.

---

### DEF-006: Playwright Staff Smoke Navigation Route Mismatch
* **Date Identified**: 15 November 2026
* **Severity**: Medium (Automated Test Failure)
* **Component**: Automated Testing Suite (`scripts/staff_design_smoke.py`)
* **Symptom**: Playwright test timed out while waiting for navigation response on the Services page.
* **Root Cause**: The smoke script awaited an API response ending in `/api/v1/services`. However, staff users are routed to `/api/v1/staff/services` (which includes draft services and management controls).
* **Remediation**:
  1. Updated the route mapping dictionary in `scripts/staff_design_smoke.py` from `/services` to `/staff/services`.
  2. Updated the revision chip regex to accommodate version badges.
* **Verification**: `scripts/staff_design_smoke.py` executed 15/15 checks with 0 page errors.

---

### DEF-007: Stale UI Element Locator in Login Smoke Suite
* **Date Identified**: 15 November 2026
* **Severity**: Low (Test Script Maintenance)
* **Component**: Automated Testing Suite (`scripts/login_smoke.py`)
* **Symptom**: `login_smoke.py` failed with `Locator expected to be enabled: get_by_role("button", name="Refresh current view")`.
* **Root Cause**: The test script asserted an obsolete header icon button that had been consolidated into the User Menu popup during earlier UI cleanup.
* **Remediation**:
  1. Removed the assertion for the deprecated button.
  2. Added assertion verifying the staff "Automation" button and role-aware navigation.
* **Verification**: `scripts/login_smoke.py` passes 6/6 browser checks cleanly.

---

### DEF-008: Seed User Password Hash Desynchronization
* **Date Identified**: 15 November 2026
* **Severity**: High (Authentication Failure)
* **Component**: Authentication & Database Seed
* **Symptom**: Live API smoke test failed on student login with HTTP 401 `INVALID_CREDENTIALS`.
* **Root Cause**: The database had been seeded with an older Argon2 hash from a prior development run that did not match the current password specified in `.env` (`SDRT_SEED_PASSWORD`).
* **Remediation**:
  1. Executed a migration script that regenerated Argon2id password hashes for all seed accounts (`student@example.test`, `other@example.test`, `registrar@example.test`) directly from `settings.seed_password`.
* **Verification**: Both student and registrar logins verified in API smoke tests and Playwright browser sessions.

---

## 3. Defect Prevention & Regression Guardrails

To prevent future regression:
1. **Pre-commit Automation**: All Dart files are continuously checked via `flutter analyze` and `flutter test`.
2. **Deterministic Seed Scripts**: `backend/app/seed.py` dynamically hashes `settings.seed_password` using Argon2id with 3 iterations and 64 MB memory cost.
3. **Multi-Viewport Headless Suites**: Playwright suites run in CI/local scripts covering desktop ($1440\,\text{px}$) and mobile ($390\,\text{px}$) viewport breakpoints.
