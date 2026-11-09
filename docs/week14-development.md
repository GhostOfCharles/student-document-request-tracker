# Week 14 development status

## Scope and source of service rules

On 9 November 2026, the user authorized the next development phase and chose University of La Salette, Inc. (ULS), Philippines as the reference institution. The user supplied no confirmed ULS registrar policies, fees, requirements or processing times. Two draft examples use common document-request concepts, not official ULS rules. They are labeled provisional, are inactive, and must be reviewed before publication. The three-day estimate and unpaid setting are placeholders.

The [ULS registrar page](https://uls.edu.ph/offices/registrar/) identifies the registrar office but does not establish the document-specific policy needed by this application. The [University of the Philippines Open University document-request page](https://registrar.upou.edu.ph/request-documents/) provides an example of Philippine registrar services; its rules and fees are not ULS policy and have not been attributed to ULS.

## Implemented development features

- A permitted registrar can create a service draft, configure text/select/date/checkbox/file requirements and optional manual payment evidence, preview the saved student form, publish a version, and change availability.
- The API checks the service-management permission, field limits and optimistic row version. Publication freezes the version; historical requests and corrections remain pinned to their original version. Service announcements are queued as durable, deduplicated jobs.
- Students can create development-only accounts with a student number, edit email/phone and change passwords. Registration does not verify student-number ownership. Production registration is disabled. Password changes revoke all sessions; a staff member with a temporary-password flag must change it before using protected functions.
- Student cancellation in the allowed states and the core request, correction and release workflow were already present in Week 13. The shared design system remains in use.

The schema already contained the necessary account and versioned-service tables, so this phase adds no Alembic revision. No real student or institutional record was imported.

## Local demonstration

Start MySQL in Laragon and open PowerShell in the project root. Rebuild Flutter after source changes:

~~~powershell
flutter pub get
flutter build web --no-wasm-dry-run
$env:PYTHONPATH = 'backend'
& backend/.venv/Scripts/python.exe -m app.provision_week14_demo
& backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
~~~

The provisioning command only runs against a loopback development database. It grants service-management permission to the existing controlled registrar and creates example Enrollment and Transcript drafts if absent. It never publishes them or replaces existing passwords and service versions. It was run on the local development database during this work. Sign out and sign back in to refresh an existing staff session.

In a second terminal at the same project root:

~~~powershell
$env:PYTHONPATH = 'backend'
& backend/.venv/Scripts/python.exe -m app.automation.scheduler
~~~

Open http://localhost:8000. Sign in as registrar@example.test with the seed password from the local ignored .env file. Open Services, select an example draft, edit and save it, then preview it. The draft editor warns before discarding changes and requires saved changes before preview or publication. Publishing and making a service available lets student accounts see it; do so only after reviewing the provisional wording. The original Week 13 test services remain available.

To exercise registration, choose Create student account on the login page and enter invented test information. The confirmation there describes development use; it is not an institutional privacy notice or an approved production registration process.

## Verification and limits

The Week 14 tests are in backend/week14_tests and use a separate migrated MySQL database whose name ends in _test. They cover account registration and role restrictions, password changes and temporary-password restrictions, service permissions, draft validation and conflicts, publication/availability, student request version pinning, and deduplicated announcements. Their fixture adds synthetic records; it does not clear that database. Set SDRT_DATABASE_URL to a separate disposable MySQL schema, SDRT_ENVIRONMENT=test and PYTHONPATH=backend before running:

~~~powershell
& backend/.venv/Scripts/python.exe -m pytest backend/week14_tests -q --tb=short
~~~

On this workstation the first attempt to migrate Laragon's empty sdrt_test failed with MySQL error 1419: binary logging was enabled and the migration account could not create triggers. The empty tables left by that failed attempt were removed after checking they contained no rows. Tests then ran against a separate local MySQL 8.4 instance on port 3307 with a dedicated disposable test schema. No Laragon global settings were changed.

Results and browser coverage are summarized in evidence/week14/verification.md. Existing Week 13 evidence is historical; it was not overwritten by the isolated regression run.

Still needed before real use: official ULS requirements, fees, payment instructions, processing times and release rules; institution-approved identity verification, privacy/retention and access policies; deployment and operational ownership; and review of the missing instructor module/rubric. This is not an institutional deployment. Full wireframe-to-route mapping and later academic assessments are not claimed.
