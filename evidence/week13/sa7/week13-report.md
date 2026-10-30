# Week 13 SA7 implementation report

30 October 2026, Asia/Manila. The feasible Week 13 vertical slice is implemented and locally verified with Flutter Web, FastAPI, MySQL 8.4.13 and one separate APScheduler 3.11.2 process. The project DOCX and its relevant tables were read and preserved. The named instructor course-module DOCX was not present in the repository or searched Downloads/Documents/Desktop/Projects directories; its local path was requested but not supplied. Consequently the implementation can be substantiated against AGENTS.md and the project's Week 13 tables, while independent Module 13 academic acceptance remains BLOCKED.

## Functional acceptance

| Views / requirement | Result and actual evidence |
| --- | --- |
| A01 | PASS: synthetic student/registrar login, Argon2id, opaque sessions, expiry/revocation, roles and CSRF/origin enforcement |
| S01 / T01 | PASS: database counts, recent requests, navigation and staff permanent-failure count |
| S02–S03 | PASS: two active published services with full versioned requirements, one without payment and one with fictional manual evidence |
| S04–S05 | PASS: configured text/select/date/checkbox/file renderer, private upload, server validation and confirmed tracking number |
| S06–S07 | PASS: owner-scoped requests, pinned details, authorized evidence, status history and immutable revision viewing |
| S08 | PASS: only named correction elements can change; complete new revision; prior revision/receipt retained; due date extended once |
| S09 / T07 | PASS: actual durable notifications, recipient-only lists and idempotent read behavior |
| T02–T03 | PASS: queue, begin review, payment review, correction, approve/reject, processing, readiness and actual handover; student completes by acknowledgement |
| T09 | PASS: actual summary, alerts, jobs, safe errors, ordered attempts, runs and audit records; allowlisted retries and manual handling |
| Shared states / responsive | PASS: loading/empty/invalid/unauthorized/API errors and actual offline/recovery path; keyboard entry and accessible labels; 1440×1000 and 390×844 captures |
| Week 13 source / schema | PASS: real API/MySQL transactions, 23 core entities plus Alembic, two migrations and 22 immutability triggers |
| Activity 1 | PASS authored comparison for three workflows with at least two alternatives each, six decision criteria, boundary/ownership/human points and adverse case; exact module match NOT RUN |
| Activity 2 | PASS actual transient/permanent/interrupted tasks, exact notification counts, bounded retry ceilings, retained evidence and authorized recovery |
| SA7 reproducible portfolio | PASS feasible source, setup, manifests, contract, diagrams, logs, tests, screenshots, recovery and maintainability notes |
| Instructor's exact Module 13 rubric and academic components | NOT RUN / BLOCKED: source module absent; quizzes/oral components and instructor grading were not performed |

The final full browser run completed SDRT-2026-000006, revision 2, at the real API. It included a payment-denied adverse response, targeted supporting-evidence correction, re-review of revision 2 payment, approval, readiness, release and student acknowledgement. Verification/browser-events.json records actual events, viewports and an empty page-error list. No real student or payment data was used.

## Actual verification matrix

All commands were run from repository root with backend/.venv/Scripts/python.exe and PYTHONPATH=backend where applicable.

| Command / check | Status | Evidence |
| --- | --- | --- |
| flutter analyze | PASS — no issues | logs/flutter-analyze-final.log |
| flutter test | PASS — 4 tests | logs/flutter-test-final.log |
| flutter build web --no-wasm-dry-run | PASS — real release output | logs/flutter-build-final.log |
| python -m pytest backend/tests -v -s --tb=short | PASS — 13 tests; 1 dependency deprecation warning | logs/pytest.log |
| python -m alembic -c backend/alembic.ini upgrade head | PASS — development upgrade and fresh disposable MySQL upgrade via fixture | verification/mysql-schema.json; logs/pytest.log; migrations logs |
| python scripts/api_smoke.py | PASS — 9 real HTTP checks | verification/api-smoke.json |
| python scripts/browser_demo.py | PASS — paid lifecycle, revisions, responsive views, offline recovery, notifications and monitoring | logs/browser-final.log; verification/browser-events.json; screenshots/ |
| python scripts/monitor_failure_demo.py against test_server.py | PASS — actual failed-job UI and manual resolution | logs/browser-failure-monitor.log; verification/browser-failure-monitor.json |
| python -m app.automation.scheduler | PASS — startup scans, real minute processing, recorded runs and delayed current-date summary behavior | logs/scheduler.log |
| Second scheduler process | PASS — correctly rejected while designated process held MySQL ownership lock | logs/scheduler-second-instance.log |
| Source configuration scan | PASS — generated local secrets absent from staged files; .env/.private/.venv ignored | verification/results.json; final Git review |
| Actual 17:00 or 02:00 wall-clock waiting | NOT RUN — tasks tested through controlled times/startup and actual scheduler registration; no claim of days of uptime | Activity 2 interpretation; scheduler source/logs |
| Instructor approval/title/FastAPI approval | NOT RUN / unverified external requirement | No approval claimed |
| GitHub push/collaborator acceptance | NOT RUN — local repository only, no remote configured | Git history and README handover instructions |
| Concept quiz/oral assessment/actual student UAT | NOT RUN | Not claimed |

Schema tests run against MySQL, never SQLite. They verify actual migration structures, immutable-history guards, typed inputs, permission/ownership boundaries, session expiry, upload parsing and limits, note privacy, canonical replay, concurrent submission/staff updates, payment gating, correction retention, aging/escalation, summary/cleanup, retries and lease fencing.

## Automation outcomes

The dedicated scheduler successfully delivered real status jobs created by the browser workflow. Notification creation and successful job/attempt finalization are atomic. Aging/escalation scans create distinct episode alerts, repeat without duplication and suspend staff-delay alerts for Needs Correction. Summaries count six pending states in a consistent snapshot keyed to Asia/Manila date.

The final controlled test snapshot contains transient job 40 (attempt 1 transient_failure, attempt 2 succeeded), permanent configuration job 41 (one permanent_failure, exposed directly to staff and resolved through the authorized API), ceiling job 42 (stopped at 3, 6 and 9 with a rejected third manual cycle) and interrupted job 43 (preserved interrupted attempt, recovered success, one notification and rejected stale finalization). A separate browser session then displayed job 42 and all nine attempts, offered no further retry, and recorded an actual staff manual-resolution note. Manual resolution does not assert delivery succeeded.

See activity2/observed-jobs.json, logs/automation-tests.jsonl, activity2/interpretation.md and sa7/recovery.md. Controlled clock values explain future attempt dates; event log timestamps are real UTC. The tests do not establish every possible physical failure or production durability condition.

## Files and design

The existing root Flutter template was retained and replaced with a real API-backed client in lib/main.dart, api.dart, requirements_form.dart and conditional platform adapters; tests are in test/widget_test.dart. Backend modules separate sessions, schemas, services, request workflow, files, operations and automation. Manifests are pubspec.yaml/pubspec.lock and backend/requirements.txt/requirements.lock.txt.

Migrations: 0001_week13 creates the 23 core Chapter 5 tables and immutable history/published-version triggers from a frozen schema snapshot. 0002_published_children prevents new requirements/options from being inserted into an already published version. No password-reset table or staff service editor was added. Schema inventory is in verification/mysql-schema.json.

Source documents, API/OpenAPI, progress/decisions and architecture are under docs/. Week 13 activities, logs, screenshots, verification and SA7 notes are under evidence/week13/. Root AGENTS.md already contained the supplied boundary and was preserved. No later assessment directory was created.

Meaningful defects found and repaired: Alembic import-path handling; local MySQL trigger privilege; scan and summary lock release across transaction commits; first-read timestamp mismatch; private-download Cache-Control overridden by common middleware; installed file-picker API differences; ambiguous upload labels and inaccessible selectable error text. Development harness fixes addressed timing, accessible menu roles, keyboard input, upload completion, duplicate live-region matches and viewport initialization. Earlier failure logs remain available and are not marked PASS.

## Reproduction and current local state

Follow root README.md for exact clean setup. At handover the main FastAPI/Flutter application remains at http://localhost:8000 and isolated MySQL at 127.0.0.1:3307. Generated credentials are only in the ignored .env and private tools directory. The scheduler and temporary port-8001 test API were stopped after capture to freeze evidence; restart the worker to continue scheduled delivery.

~~~powershell
$env:PYTHONPATH = 'backend'
& backend/.venv/Scripts/python.exe -m alembic -c backend/alembic.ini upgrade head
& backend/.venv/Scripts/python.exe -m app.seed
flutter pub get
flutter build web --no-wasm-dry-run
& backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
~~~

In a separate root terminal:

~~~powershell
$env:PYTHONPATH = 'backend'
& backend/.venv/Scripts/python.exe -m app.automation.scheduler
~~~

Do not start another API on an occupied port; the above is the reproducible startup sequence for a stopped environment. Controlled accounts are student@example.test, other@example.test and registrar@example.test, all using the operator-selected SDRT_SEED_PASSWORD. Two version-1 synthetic services are seeded. For the repeatable demonstration use separate browser profiles/contexts for student and registrar and the root README's numbered flow.

The local implementation source commit is 27884a6fdd06cad8660f5a4b5699512855a558cf. The report-containing final evidence commit is the subsequent local HEAD; use git log -1 --oneline and verification/source-hashes.json to inspect it. No prior Git repository existed, so no historical work or remote push was invented. Instructor collaborator instructions are in README.md.

## Remaining limitations and stop

The exact instructor module/rubric is the outstanding source blocker; external title/backend approval and collaborator acceptance are unverified. This is a synthetic local prototype, not production readiness or actual registrar UAT. The UI uses explicit refresh and bounded lists of 100; the API has pagination. The scan/summary approach targets the small demonstration dataset and has not been production-sized. Login throttling is process-local. The notification handler is deliberately short and database-only; long external handlers are not part of this slice. The test library emits a deprecation warning without failing the checks.

No known failing required workflow remained in the final executed tests/browser run. Earlier preliminary browser captures/logs may show a defect before repair; the final files listed in the matrix establish the verified state. Code/test results do not complete quizzes, oral work, instructor acceptance or a grade.

Weeks 14–18 are not implemented or assessed by this assignment. Work stops after this Week 13 report; no later milestone is started.
