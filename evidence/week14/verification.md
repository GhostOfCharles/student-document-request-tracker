# Week 14 development verification

Observed locally on 9 November 2026. All browser accounts, documents, student numbers and requests were invented test data. The instructor's Week 14 module/rubric was not available; these checks are implementation evidence, not instructor approval or a grade.

| Check | Result | What was observed |
| --- | --- | --- |
| flutter analyze | PASS | No issues after the frontend changes. |
| flutter test | PASS | Six Flutter tests passed, including the saved-draft preview and configured payment fields. |
| flutter build web --no-wasm-dry-run | PASS | Web build completed. |
| pytest backend/week14_tests -q --tb=short | PASS | Six MySQL-backed checks, including registration, profile/password, temporary staff passwords, manager permissions, service version pinning, duplicate announcements and cancellation. One dependency deprecation warning. |
| pytest backend/tests -q --tb=short | PASS | Thirteen existing Week 13 tests passed from an isolated copy against a separate disposable MySQL schema. One dependency deprecation warning. Existing Week 13 evidence files were not overwritten. |
| Initial Laragon test-schema migration | FAIL | MySQL error 1419 prevented trigger creation with binary logging enabled. No application-database migration was attempted. The newly created empty test tables were removed after verifying that they contained no rows. |
| Isolated MySQL migration | PASS | Existing migrations completed on a separate loopback MySQL 8.4.13 test schema with trigger creation enabled for that isolated server. |
| Desktop browser workflow | PASS | In an isolated test database, a manager edited, saved, previewed and published a provisional draft; a newly registered test student submitted a request using it and updated contact details. |
| New service creation in browser | PASS | A manager created a draft with a requirement label and no manual field key; the key was generated and the student-form preview displayed it. |
| Narrow browser workflow | PASS | At 390 × 844, registration, draft editor, unsaved-change confirmation and forced temporary-password change were exercised. |
| Service search in browser | PASS | A registrar searched for a matching service by code. |
| ULS official requirements, fees and processing times | NOT VERIFIED | ULS has not confirmed the provisional examples. |
| Real student identity, real payment, deployment and user acceptance | NOT RUN | No institutional system or real records were used. |
| Instructor's exact Week 14 module and assessment | NOT RUN | Source module and instructor confirmation were not available. |

Screenshots in screenshots/ are actual captures from the isolated browser checks; some were taken during the preceding iteration of the same UI, before final wording and layout refinements. Browser scripts and temporary database configuration used for this local run are under the ignored .private directory. The reproducible backend test source is backend/week14_tests/test_service_accounts.py; see docs/week14-development.md before running it.
