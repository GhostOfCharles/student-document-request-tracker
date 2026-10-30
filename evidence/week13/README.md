# Week 13 SA7 evidence index

Verified local development implementation for Advanced Automation and Scripting. Only synthetic data was used. This portfolio records working source and actual execution; it is not instructor approval or a completed academic grade. The instructor course-module DOCX was unavailable, so independent confirmation against its exact Module 13 rubric remains BLOCKED.

Read sa7/week13-report.md for the acceptance audit, limitations, commands, local runtime state and repository references. Root README.md gives setup and a repeatable student/registrar demonstration.

| Evidence | Location |
| --- | --- |
| Source project and authoritative table extraction | docs/specification/ |
| Week 13 task status and decisions | docs/implementation-progress.md; docs/implementation-decisions.md |
| Architecture, trust boundary, lifecycle and triggers | docs/architecture/week13.md |
| Implemented API contract and generated models | docs/api-contract.md; docs/api-openapi.json |
| Activity 1 three-workflow comparison and interpretation | activity1/decisions.md |
| Activity 2 expected/observed outcomes, clock explanation and reproduction | activity2/interpretation.md |
| Queried durable failure jobs and attempts | activity2/observed-jobs.json |
| Actual JSON automation events | logs/automation-tests.jsonl |
| MySQL migration, permission, lifecycle, concurrency, file and retry verification | logs/pytest.log; verification/mysql-schema.json |
| Flutter analysis, four tests and release build | logs/flutter-analyze-final.log; logs/flutter-test-final.log; logs/flutter-build-final.log |
| Live HTTP API smoke checks | logs/api-smoke.log; verification/api-smoke.json |
| Final browser workflow, real keyboard input and responsive captures | logs/browser-final.log; verification/browser-events.json |
| Staff failure monitoring and manual resolution | logs/browser-failure-monitor.log; verification/browser-failure-monitor.json |
| Dedicated scheduler startup, actual minute delivery and duplicate-process rejection | logs/scheduler.log; logs/scheduler-second-instance.log |
| Recovery and maintainability | sa7/recovery.md; sa7/maintainability.md |
| Final verification matrix and source hashes | verification/results.json; verification/source-hashes.json |
| Defects found and repaired | sa7/week13-report.md; earlier logs retained under logs/ |

Paths in the table are repository-relative when they begin docs/; others are relative to evidence/week13. Preliminary *initial*, *second*, numbered browser, before-fix and non-final logs document failed/interrupted development attempts. They are not acceptance PASS evidence. Empty successful Alembic command logs are corroborated by the real schema inventory and pytest's fresh migration execution.

Principal actual browser captures:

- login-desktop.png and login-validation.png
- student-dashboard-desktop.png, services-desktop.png and service-requirements.png
- dynamic-form-desktop.png, filled-submission-form.png and submission-confirmation.png
- staff-review-payment.png, adverse-payment-not-verified.png and correction-form.png
- completed-timeline-desktop.png, immutable-original-revision.png and tracking-narrow.png
- services-narrow.png, network-error-narrow.png and student-notifications-narrow.png
- automation-monitor-desktop.png and automation-monitor-narrow.png
- permanent-failure-attempts-desktop.png and manual-resolution-narrow.png

The full workflow run completed request SDRT-2026-000006 with two immutable revisions and no page errors. Earlier development attempts left other synthetic requests and unused staging files in the development database; these are real records, not hidden/fabricated results. The test database is separate and rebuilt by pytest.

The attempt experiment uses explicit controlled eligibility clocks; some attempt dates are simulated future dates, while structured event timestamps are actual wall-clock UTC. See Activity 2 before interpreting them. The browser monitor subsequently resolves the exhausted test job, so its later snapshot differs legitimately from the pre-resolution observed-jobs.json.

STOP boundary: Weeks 14–18 are not implemented or assessed. Registration, service editor, real recovery, production deployment and actual user acceptance are outside this evidence.
