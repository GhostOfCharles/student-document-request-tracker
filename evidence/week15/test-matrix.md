# Week 15 Integration & Usability Test Matrix

**Project**: Student Document Request Tracker  
**Milestone**: Week 15 — Integration, Usability Testing & Defect Resolution  
**Date**: 15 November 2026  
**Target Environment**: Windows 11, Flutter Web 3.47.7, FastAPI 1.0.0, MySQL 8.4.3 (Laragon), Microsoft Edge  

---

## 1. Scope & Verification Dimensions

Per the course milestone specifications for **Week 15**, the test suite systematically exercises six core operational dimensions:
1. **Request Lifecycle & State Machine**: Valid linear workflow transitions and blocking of all invalid/out-of-order transitions.
2. **Role-Based Access Control (RBAC)**: Enforcing clear authorization boundaries between Student, Staff, and Manager roles.
3. **File Upload & Private Storage**: Multipart validation, size bounds, MIME filtering, private staging, and protected download paths.
4. **Concurrency & Race Conditions**: Optimistic locking (`row_version`), double-click action deduplication, and worker interruption fencing.
5. **Responsive Layout & Usability**: Multi-viewport layout adaptation ($\ge 900\,\text{px}$ two-column split vs $< 900\,\text{px}$ stacked layout), touch-target ergonomics, and visual hierarchy.
6. **Error Handling & Security Invariants**: Sanitized API error envelopes, CSRF renewal, Argon2id credentials, and MySQL trigger immutability.

---

## 2. Comprehensive Test Matrix

| ID | Category | Scenario / Invariant | Preconditions | Input / Action | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|---|---|
| **TM-SM-01** | State Machine | Linear progression: Draft to Under Review | Request submitted by student | Staff executes `begin_review` | Status transitions from `submitted` to `under_review`; audit log and timeline recorded | Transition successful; timeline displays timestamp and staff ID | **PASS** |
| **TM-SM-02** | State Machine | Correction round request | Request in `under_review` | Staff flags requirement and provides instructions | Status transitions to `correction_requested`; student notification generated; non-flagged inputs locked | Notification delivered; student edit view enables flagged fields only | **PASS** |
| **TM-SM-03** | State Machine | Block invalid jump: Direct Completion | Request in `submitted` | Client attempts to transition directly to `completed` | HTTP 409 Conflict (`INVALID_STATE_TRANSITION`); transition rejected | 409 Conflict returned; request remains in `submitted` state | **PASS** |
| **TM-SM-04** | State Machine | Payment gate enforcement | Service requires fee; request in `under_review` | Staff attempts `mark_ready_for_release` without payment record | Action rejected: payment verification required before document release | System demands verified receipt; release action disabled | **PASS** |
| **TM-SM-05** | State Machine | Student acknowledgment | Document in `released` state | Student reviews completed document and clicks "Acknowledge Receipt" | Status advances to `completed`; final timestamp recorded; request archived from active queue | State updated to `completed`; milestone stepper displays 100% | **PASS** |
| **TM-RB-01** | RBAC | Student denied staff endpoints | Authenticated as student (`TEST-001`) | GET `/api/v1/staff/automation/jobs` | HTTP 403 Forbidden (`FORBIDDEN`); access blocked | HTTP 403 returned with safe error payload | **PASS** |
| **TM-RB-02** | RBAC | Cross-student request isolation | Authenticated as `TEST-002` | GET `/api/v1/requests/{id_of_TEST-001}` | HTTP 404 Not Found (or 403) to prevent request enumeration | Request not found / inaccessible to unauthorized student | **PASS** |
| **TM-RB-03** | RBAC | Manager-only service publication | Authenticated as standard registrar staff | POST `/api/v1/staff/services/{id}/publish` | HTTP 403 Forbidden; only users with `can_manage_services=True` permitted | Blocked for non-manager; permitted for service manager | **PASS** |
| **TM-RB-04** | RBAC | Temporary password enforcement | Account flagged with `must_change_password=True` | User attempts to navigate to dashboard | Route guarded: user forced into Password Change modal before any operational access | Modal cannot be dismissed until new password accepted | **PASS** |
| **TM-UP-01** | File Upload | Valid file attachment | Authenticated user; file within bounds | Upload 3.0 MB PNG image | 201 Created; private staging storage assigned; SHA-256 hash calculated | Upload stored; metadata recorded in `stored_files` | **PASS** |
| **TM-UP-02** | File Upload | Oversized file rejection | Valid session | Upload file $> 10\,\text{MB}$ (e.g. 15 MB PDF) | HTTP 413 Payload Too Large (`FILE_TOO_LARGE`); upload rejected | Rejected with 413; file not written to persistent storage | **PASS** |
| **TM-UP-03** | File Upload | Disallowed file extension | Valid session | Upload executable file (`.exe` / `.bat`) | HTTP 415 Unsupported Media Type (`UNSUPPORTED_FILE_TYPE`) | File rejected with 415 error | **PASS** |
| **TM-UP-04** | File Upload | Staged file isolation | Uploaded to staging | Access file directly without signed token | Access denied; raw file paths not exposed through public web server | Private storage token required; direct URL yields 403/404 | **PASS** |
| **TM-CC-01** | Concurrency | Optimistic locking on concurrent review | Two staff members open same request (`row_version=1`) | Staff A approves; Staff B submits correction with stale `row_version=1` | Staff A succeeds (`row_version` becomes 2); Staff B receives 409 Conflict (`REVISION_CONFLICT`) | Second write rejected; UI refreshes to show current status | **PASS** |
| **TM-CC-02** | Concurrency | Idempotent student submission | Student on slow connection | Rapid duplicate clicks on "Submit Request" | Client-side debouncing and server `client_submission_key` prevent duplicate rows | Single request created; second request returns identical response | **PASS** |
| **TM-CC-03** | Concurrency | Worker fencing token | Automated scan running | Second scheduled worker instance started concurrently | Second instance detects active lock and terminates gracefully without corrupting state | Lock acquired by instance 1; instance 2 logs standby message | **PASS** |
| **TM-UI-01** | Usability / UI | Desktop Two-Column Split ($\ge 900\,\text{px}$) | Desktop viewport ($1440 \times 950$) | Open Request Review & Detail screen | Left 65% displays Requirements & Activity; Right 35% displays Action Card, Student Profile & Stepper | Layout renders cleanly side-by-side with zero horizontal overflow | **PASS** |
| **TM-UI-02** | Usability / UI | Mobile Stacked Priority ($< 900\,\text{px}$) | Mobile viewport ($390 \times 844$) | Open Request Review & Detail screen | Stacked layout: Action panel appears first at top; Student Profile second; Requirements & Stepper below | Action buttons immediately reachable without scrolling past data | **PASS** |
| **TM-UI-03** | Usability / UI | Extreme narrow layout ($320\,\text{px}$) | Ultra-compact screen ($320 \times 600$) | Navigate Dashboard and Request List | Card headers wrap gracefully; metric counters remain legible; 0 pixel overflows | Visual test passes at 320px with zero layout assertion errors | **PASS** |
| **TM-UI-04** | Usability / UI | Document attachment card ergonomics | Request has attached proof files | Inspect document requirement cards | File icon badges (Image/PDF), formatted sizes (KB/MB), and inline View buttons | Cards render with rounded borders, distinct icons, and preview links | **PASS** |
| **TM-UI-05** | Usability / UI | Inline staff activity composer | Staff reviewing request | Click "Add Note", select visibility, and submit | Note added to inline activity feed immediately without page refresh; tag chips visible | Feed updates in real time; student-visible vs staff-only tags shown | **PASS** |
| **TM-EH-01** | Error Handling | Database trigger immutability mapping | Published service version in MySQL | Direct SQL or API update attempted on published requirement | MySQL trigger raises SQLSTATE 1644; backend catches and maps to safe 409 Conflict | Trigger blocks write; user receives clean error envelope | **PASS** |
| **TM-EH-02** | Error Handling | Sanitized authentication failure | Sign-in page | Enter non-existent user or wrong password | Error message: `"The sign-in details are invalid. (INVALID_CREDENTIALS)"`; no account enumeration | Message identical for bad user and bad password | **PASS** |
| **TM-EH-03** | Error Handling | CSRF protection & token renewal | Authenticated session | Post action with missing or mismatched `X-CSRF-Token` | HTTP 403 Forbidden (`CSRF_FAILED`); token refreshed on subsequent fetch | Action blocked until valid CSRF token supplied | **PASS** |

---

## 3. Automated Test Execution Results

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.3.4, pluggy-1.5.0
rootdir: C:\Users\Charles\Coding\Flutter\Student Document Request Tracker\student_document_request_tracker\backend
configfile: pyproject.toml
collected 19 items

tests/test_api.py .............                                          [ 68%]
week14_tests/test_service_accounts.py ......                             [100%]

======================== 19 passed, 2 warnings in 16.79s =======================

$ flutter test
00:02 +17: All tests passed!

$ flutter analyze
Analyzing student_document_request_tracker...
No issues found! (ran in 1.8s)
```

## 4. Usability & Ergonomics Assessment

* **Cognitive Load Reduction**: Consolidating requirement data into structured key-value property grids and visual document badges eliminated the wall of unformatted text.
* **Focal Review Path**: Placing the Action Card and Milestone Stepper in a dedicated sticky right sidebar (Desktop) or top slot (Mobile) ensures registrars never have to search for the next operational step.
* **Audit Transparency**: Inline notes with explicit privacy badges (`Staff Only` vs `Student Visible`) provide full contextual clarity before notices are dispatched to students.
