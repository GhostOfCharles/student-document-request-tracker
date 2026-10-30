# Student Document Request Tracker — Week 13 SA7

Working Flutter Web + FastAPI + MySQL development prototype for Advanced Automation and Scripting. All accounts and evidence are synthetic. See evidence/week13/README.md for verified results and the acceptance boundary. The instructor Module 13 DOCX was not found locally; independent module/rubric confirmation is blocked. Instructor project/title and FastAPI approval are unverified.

## Requirements

Flutter stable with Dart, Python 3.11 or newer, MySQL 8.0.16+ (verified here with 8.4.13), and a modern Chromium browser. No SQLite substitute is supported. The existing Flutter project remains at repository root. Python dependencies are in backend/requirements.txt and the executed environment is pinned in backend/requirements.lock.txt.

## Database and configuration

Create two development databases with an administrator in the MySQL client. Replace all example placeholders locally; do not commit credentials.

~~~sql
CREATE DATABASE sdrt CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE sdrt_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'sdrt'@'127.0.0.1' IDENTIFIED BY 'YOUR_RANDOM_LOCAL_PASSWORD';
GRANT ALL PRIVILEGES ON sdrt.* TO 'sdrt'@'127.0.0.1';
GRANT ALL PRIVILEGES ON sdrt_test.* TO 'sdrt'@'127.0.0.1';
~~~

MySQL binary logging may require the administrator to authorize trigger creation for the migration account. On the isolated classroom server used here, the administrator enabled log_bin_trust_function_creators. Do not grant SUPER to the application account. This prototype uses one development database account for migrations and runtime; production credential separation is not claimed.

Official ZIP installation and initialization references: [Windows archive installation](https://dev.mysql.com/doc/mysql-installation-excerpt/8.0/en/windows-install-archive.html) and [MySQL initialization](https://dev.mysql.com/doc/refman/8.4/en/data-directory-initialization.html). The local verification server is an isolated binary install under %LOCALAPPDATA%\SDRT-week13-tools, bound only to 127.0.0.1:3307, with mysqlx disabled. It is not a Windows service. Its generated administrator password is stored outside the repository in that private tools directory; no empty root login remains.

To restart that already-initialized workstation instance after a reboot (only when port 3307 is free):

~~~powershell
$sdrtTools = Join-Path $env:LOCALAPPDATA 'SDRT-week13-tools'
Start-Process -FilePath "$sdrtTools/mysql-8.4.13-winx64/bin/mysqld.exe" -ArgumentList @('--no-defaults',"--basedir=$sdrtTools/mysql-8.4.13-winx64","--datadir=$sdrtTools/data",'--port=3307','--bind-address=127.0.0.1','--mysqlx=OFF','--log-bin-trust-function-creators=ON',"--log-error=$sdrtTools/mysql-error.log") -WindowStyle Hidden
~~~

Do not reinitialize that data directory. A clean installation uses your own initialized MySQL instance and the configuration steps below.

From the repository root in PowerShell:

~~~powershell
python -m venv backend/.venv
& backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.lock.txt
Copy-Item .env.example .env
~~~

Edit .env: set the MySQL URL and separate _test URL, choose a random CSRF secret of at least 32 characters, and set SDRT_SEED_PASSWORD to an operator-selected password of at least 12 characters. The same chosen synthetic test password is used for the three seed accounts. The current workstation already has generated values in its ignored .env; inspect that file locally to obtain the development login password. Never paste it into evidence.

Local HTTP development explicitly sets SDRT_SECURE_COOKIES=false; deployed HTTPS would require true. Use the exact allowed browser origin, including port. Private uploads are written to .private/uploads outside web assets.

~~~powershell
$env:PYTHONPATH = 'backend'
& backend/.venv/Scripts/python.exe -m alembic -c backend/alembic.ini upgrade head
& backend/.venv/Scripts/python.exe -m app.seed
flutter pub get
flutter build web --no-wasm-dry-run
~~~

Migrations create the 23 core Chapter 5 tables, indexed foreign keys, constraints and immutable-history triggers. Alembic also creates its version table. Seed is repeatable and does not overwrite existing passwords or published versions.

## Run the application

In one root PowerShell terminal:

~~~powershell
$env:PYTHONPATH = 'backend'
& backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
~~~

In a second root terminal, start exactly one dedicated scheduler:

~~~powershell
$env:PYTHONPATH = 'backend'
& backend/.venv/Scripts/python.exe -m app.automation.scheduler
~~~

Open http://localhost:8000 after building Flutter and starting/restarting FastAPI. FastAPI serves the real Flutter build and /api/v1 on the same origin. Swagger is at http://localhost:8000/docs. An unknown API path stays an API 404. Build changes require another Flutter build; restart FastAPI if it was started before build/web existed.

For Flutter development in a third terminal, with the API still running:

~~~powershell
flutter run -d web-server --web-hostname localhost --web-port 5173 --dart-define=API_BASE=http://localhost:8000/api/v1
~~~

Use localhost consistently so same-site development cookies work. The configured origin list permits localhost:5173 with credentials; it does not allow arbitrary origins. A protected browser cookie carries the session; no token is stored in browser local storage.

## Controlled accounts and services

| Account | Role |
| --- | --- |
| student@example.test or TEST-001 | Synthetic student |
| other@example.test or TEST-002 | Second student for ownership checks |
| registrar@example.test | Synthetic registrar staff |

Certificate of Good Moral version 1 has no payment. Certificate of Enrollment version 1 requires a fictional reference, separate fictional receipt and supporting evidence. Both versions include server-configured text/select/date/checkbox/file requirements. Payment is manual evidence review; no money is collected.

## Repeatable demonstration

1. Sign in as the first student. Inspect the actual dashboard and two published services. Open a service's configured requirements, then Create request.
2. Enter a synthetic purpose, select a category and confirm synthetic data. The date is optional in the seeded versions. For Enrollment, upload supporting PDF/JPEG/PNG and a separate fictional receipt; enter a fictional reference. Each file is at most 5 MiB; the server verifies content.
3. Submit and confirm. Keep the server-confirmed SDRT tracking number. My Requests shows the real timeline and revision.
4. In another browser profile/context, sign in as registrar. Open Requests and select that tracking number. Begin review. Attempting approval without verified payment returns PAYMENT_NOT_VERIFIED.
5. Request correction for a named requirement and enter meaningful instructions. Refresh the student's detail, correct only the targeted element, and resubmit. View revision 1 to verify previous evidence is preserved.
6. Registrar refreshes, verifies payment against revision 2, approves requirements, marks ready, and confirms actual handover. Student refreshes and acknowledges receipt. The final state is Completed.
7. Wait up to one worker interval for real notifications. Read a notification and inspect staff Automation: summary, alerts, jobs, attempts and sanitized activity. Generate the current local-date summary; previous-date regeneration is rejected.
8. Run the controlled failure experiment through pytest below. Its synthetic clock advances retry eligibility without changing production schedules. Inspect activity2/observed-jobs.json and logs/automation-tests.jsonl. Staff monitoring HTTP authorization and manual recovery are exercised against the test database, independently of the browser demonstration's development database.

## Verification

Run from repository root; pytest resets only the database explicitly named by SDRT_TEST_DATABASE_URL and ending in _test. Do not point it at records you need.

~~~powershell
flutter analyze
flutter test
flutter build web --no-wasm-dry-run
$env:PYTHONPATH = 'backend'
& backend/.venv/Scripts/python.exe -m pytest backend/tests -v -s --tb=short
& backend/.venv/Scripts/python.exe scripts/api_smoke.py
& backend/.venv/Scripts/python.exe scripts/browser_demo.py
~~~

api_smoke.py and browser_demo.py require the actual API on port 8000. Browser automation uses installed Microsoft Edge through Playwright; on another workstation install Edge or adjust the channel to an installed Chromium. Its screenshots are actual UI captures. The test-only failure flags are internal worker inputs enabled only by SDRT_ENVIRONMENT=test; no browser failure-injection endpoint exists.

See docs/api-contract.md, docs/architecture/week13.md, docs/implementation-decisions.md, and evidence/week13/sa7/recovery.md. The detailed Week 13 report records limitations and external academic blockers. No concept quiz, oral assessment, instructor approval, GitHub push, collaborator acceptance or production readiness is asserted.

## Repository handover

The implementation is local. Review git log and the Week 13 report for the verified local commit. Create a private remote only under the user's/instructor's directions, push the reviewed source, and invite Sir Nacorda using his verified GitHub username and course instructions. Do not include .env, .private, database files or tool binaries. No invitation acceptance is claimed.

Weeks 14–18 are not implemented or assessed by this assignment. Stop at the Week 13 report.
