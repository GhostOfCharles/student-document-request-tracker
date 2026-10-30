AGENTS.md — Student Document Request Tracker (Week 13 Only)
Assignment and execution boundary
Current authorized implementation milestone: WEEK 13 ONLY — Advanced Automation and Scripting (SA7).
Build a real, working Flutter Web + FastAPI + MySQL Week 13 vertical slice of the Student Document Request Tracker. The immediate goal is a functioning browser-to-API workflow with status notifications, aging alerts, escalation, daily pending summaries, persistent retries, failure recovery, logs, and reproducible evidence. This is one continuing application for Weeks 13–18, but this assignment must stop at Week 13 acceptance.
Do not implement, assess, or report completion of Weeks 14, 15, 16, 17, or 18. Do not treat the 25 planned screens as a Week 13 completion requirement. Do not build later features simply because they appear in the master specification. After Week 13 is verified, give an honest completion report and stop, awaiting a separate Week 14 instruction.
Authoritative documents, in priority order
The instructor's Week 13 Module 13: Advanced Automation and Scripting, within PFEBSIT_002_Weeks_13-18_Student_Module_Flutter_Web.docx if supplied. Pay special attention to the Week 13 Web Deliverable, Activity 1, Activity 2, and SA7.
Student_Document_Request_Tracker_Documentation.docx, particularly Chapter 11 Week 13 minimum implementation, its Week 13 views and evidence matrix, plus the applicable database, API, status, privacy, and automation contracts. Keep the source copy under docs/specification/.
This AGENTS.md, which controls execution limits, evidence integrity, and workflow for the current coding assignment.
Read the relevant source content and tables, not merely the table of contents. If the documents differ, preserve the course module's academic requirements and the project's specific API/data conventions; record any material conflict in docs/implementation-decisions.md rather than silently inventing behavior.
Approval boundary: Instructor approval of the project/title and FastAPI backend is an external requirement, not something the code agent can assume. Do not state that it has been granted. Work exclusively with synthetic test data and development infrastructure; do not connect to a real registrar system, use live student information, or claim production readiness.
Week 13 completion objective
Demonstrate a bounded workflow using actual database-backed records and a Flutter Web client:
A test student signs in, views two seeded services (one without payment, one using fictional manual payment evidence), completes versioned dynamic fields, optionally uploads required PDF/JPEG/PNG evidence, and submits a request.
FastAPI validates the submission server-side; MySQL records the request and immutable initial revision; the student sees the tracking number and can inspect real status/history.
A test registrar staff member signs in, sees a request queue, reviews the current revision and evidence, begins review, verifies fictional payment evidence if required, approves or rejects with a reason, or requests a correction.
The student corrects and resubmits; the backend preserves the previous revision. Staff may proceed through Processing, Ready for Release, and Released. The student acknowledges receipt to Complete. Implement only the minimum UI needed to demonstrate this workflow.
Backend transactions queue real in-app status notifications; a dedicated scheduler/worker detects overdue requests and stalled conditions, creates staff aging/escalation alerts, and generates a daily pending request summary.
Demonstrate a successful automation, a transient failure recovered through bounded retry, and a permanent failure surfaced for authorized human action. Show that duplicates, endless retries, and silent data loss are prevented.
Preserve actual execution logs, tests, screenshots or recordings, setup instructions, decision evidence, recovery notes, and a maintainability evaluation in evidence/week13/.
Do not substitute static fake dashboards, hardcoded successful responses, fabricated logs, or decorative UI for working behavior.
Technology and architecture: do not substitute
Frontend: Flutter Web and Dart; Chrome/modern browser target, responsive desktop and narrow-width layout. No Android APK, iOS build, or native mobile integration.
Backend: Python FastAPI, Pydantic, SQLAlchemy, PyMySQL, Alembic.
Database: MySQL 8.0.16+ (InnoDB, utf8mb4). Do not replace it with SQLite, PostgreSQL, Firebase, or Supabase.
Automation: APScheduler 3.x, one designated scheduler/worker process, with durable automation jobs and attempts in MySQL. Do not launch a scheduler in every web worker.
Auth/security needed for this slice: Student/staff test accounts, Argon2id password hashing, backend role/ownership checks, server-managed opaque sessions, protected browser cookies and CSRF/origin protection, secret-free configuration. Keep access controls on all request and file endpoints even though deeper Week 14 evaluation is deferred.
Evidence files: PDF/JPEG/PNG stored privately outside static web assets; FastAPI authorizes every access, and the database stores metadata rather than file bytes. Use synthetic receipts only; this is manual evidence review, not a payment gateway.
Source management: One repository, truthful Git history, documented local setup, .env.example, .gitignore, no credentials or actual student records committed.
Suggested repository layout (respect working files if the repository already exists):
student-document-request-tracker/
  AGENTS.md
  frontend/                         # Flutter Web app and tests
  backend/
    app/                            # FastAPI routes, auth, models, services
      automation/                   # Scheduler, durable worker, task handlers
    migrations/                     # Alembic revisions
    tests/                          # Unit and MySQL-backed tests
  docs/
    specification/                  # Source documents
    implementation-progress.md
    implementation-decisions.md
    architecture/                   # Architecture, boundary and flow diagrams
  evidence/
    week13/
      README.md                     # Evidence index and reproduction guide
      activity1/                    # Three trigger/execution pattern decisions
      activity2/                    # Failure injection and interpretation
      logs/                         # Sanitized real execution outputs
      screenshots/                  # Actual Flutter browser captures, if available
      verification/                 # Test commands, results and regressions
      sa7/                          # SA7 case, maintainability, recovery notes
  .env.example
  .gitignore
  README.md
Do not create or populate Week 14–18 assessment folders as if those activities were performed.
Week 13 functional scope
Required working UI views
Implement only the views needed for Week 13; combine related pages into shared widgets when appropriate, but retain clear navigation and visible state feedback:
ID
Minimum functional coverage
A01
Working login for seeded student and registrar staff; role-aware routing
S01
Basic dashboard, actual counts/recent requests and navigation
S02–S03
Active service listing and full configured requirements
S04–S05
Dynamic submission form, controlled file uploads, server-confirmed submission result
S06–S07
My Requests, details, secure evidence access and status timeline
S08
Correct and resubmit with a new immutable revision
S09
In-app notification list and read behavior
T01
Basic staff dashboard with actual queue/summary data
T02–T03
Staff queue and request review, payment evidence check, correction, rejection and status progression
T07
Staff notifications and alerts
T09
Daily summary, automation status, attempts, safe manual recovery and failures

Implement necessary confirmation dialogs and the shared loading, success, empty, invalid, unauthorized, network and server-error states for the paths above. Make these routes usable on desktop and narrow browser widths. The UI can look like a skeleton; the behavior cannot be a mockup.
Required backend behavior
Apply only the documented /api/v1 routes that the Week 13 vertical slice requires. Keep their original method, request/response shape, HTTP statuses, authorization rules and naming. Do not implement the entire Chapter 6 route inventory just because it exists.
Use the documented 23-table database design as the long-term schema reference. Build the database entities and Alembic migrations required by the Week 13 flow and durable automation; creating shared foundational tables now is acceptable where genuinely needed. Do not implement later UI or workflow simply because a table exists.
Preserve immutable published service versions and submitted request revisions. Use two seeded, published services, including one with payment evidence; the full registrar service editor is not a Week 13 requirement.
Enforce status transitions and row_version concurrency checks on the server. Preserve correction rounds, notes, status history, and authorized file access.
Ensure initial submission and correction resubmission retries are idempotent, using the documented client submission keys and canonical payload hashes. Retry of identical payload must not duplicate requests or revisions.
Use persistent automation_jobs, automation_attempts, automation_runs, notifications, request_alerts, daily_request_summaries, and sanitized audit_logs as specified. Business changes and queued follow-up jobs must be committed atomically.
Implement status notifications, periodic aging checks, escalation of stalled registrar work, local-time daily summary generation, bounded transient retries, permanent-failure routing, and manual recovery only as specified.
Demo scheduled actions through controlled test times or a safe test-only trigger; do not change production timers solely to fabricate results.
Defer explicitly to later weeks
Do not build the entire 25-screen experience; detailed profile/help pages, service management draft editor/publishing UI (T04–T06), optional Save Draft, real password recovery (A03), full production deployment, full security assessment portfolio, broad Week 15 integration/regression campaign, Week 16 load/hosting evaluation, Week 17 actual UAT, and Week 18 defense are outside this assignment.
Registration A02 and account/profile editing are not essential to the first Week 13 demonstration because controlled seeded accounts are allowed. Build only if required to complete the Week 13 demonstration without detracting from SA7; otherwise defer. A03 must not offer an insecure or nonfunctional reset.
Important: Deferral does not justify weakening basic authentication, validation, protected file access, logging hygiene, or tests needed to verify the Week 13 workflow.
Week 13 academic evidence and activities
Activity 1 — Architecture and Decision
Compare trigger/execution choices for three contrasting office workflows, using the module's criteria: latency, volume, reliability, security, staffing, and ownership. Use relevant project examples: (1) request status notifications (event-triggered), (2) overdue and stalled request checking (periodic), and (3) daily pending summary (scheduled). For each, discuss at least two feasible patterns, their tradeoffs and a justified selection. Preserve assumptions, trust boundaries, human approval points, decision ownership, a workflow/trigger matrix, an adverse case, limitations, and a concise interpretation distinguishing observation from recommendation.
Activity 2 — Verification and Improvement
Conduct actual controlled failure injection on a bounded automated task. Prove with execution records that the system avoids:
Duplicate processing / duplicate notifications after retry or worker interruption.
Endless retries (bounded attempt ceiling and durable terminal state).
Silent data loss (durable pending/failed job and error evidence).
Show at least one transient failure followed by successful retry and one permanent failure routed to authorized human action. Preserve test setup, exact commands, timestamps, expected versus observed outcomes, logs, and interpretation. Do not forge failure evidence.
SA7 portfolio and web deliverable
Create an indexed, reproducible Week 13 portfolio including:
Flutter project source, backend and automation source, dependency manifests and example config without secrets.
Browser and API working demonstration, principal screen states, validation and an adverse error state.
Responsive browser evidence at desktop and narrow viewport sizes; basic accessible labels and keyboard navigation.
Architecture diagram, workflow boundary/trigger map, endpoint contract for implemented operations, and design/decision records.
Actual structured automation logs; retry attempts, transient recovery and permanent-failure evidence; explicit manual recovery procedure.
README with step-by-step MySQL setup/migrations, FastAPI, scheduler, and Flutter Web run commands.
Tests and actual PASS/FAIL/NOT RUN results, failures/fixes, reproducible verification data, and limitations.
Concise maintainability evaluation (responsibility boundaries, protected config, modularity, operational ownership, known tradeoffs) and one-page interpretation for each activity.
Truthful Git commits/references and instructor collaborator instructions; do not claim invitation acceptance or approval if unverified.
The Week 13 portfolio is incomplete if it contains only attractive screenshots or explanations without working source and reproducible tests. The course module also includes concept/quiz or oral components; do not claim those are completed by code generation.
Required execution sequence
Inspect the existing repository and tool availability; read the applicable documents and the instructor's Week 13 module. Preserve working code.
Create docs/implementation-progress.md listing Week 13 tasks only, each marked NOT STARTED / IN PROGRESS / PASS / BLOCKED with real evidence paths. Record essential decisions in docs/implementation-decisions.md.
Initialize/repair the Flutter Web frontend, FastAPI backend, MySQL connection and Alembic migrations; make a real frontend-to-API smoke request.
Implement seeded accounts, minimum sessions and roles, and two versioned published services.
Implement private file staging, dynamic form rendering, submission/revisions, tracking, staff review/correction/payment, and the minimum release/acknowledgement path.
Implement durable event notifications, APScheduler jobs, aging/escalation, daily summary, attempts, and permanent-failure review/retry.
Add meaningful frontend error states and minimal responsive layout. Implement Activity 1 and Activity 2 evidence with actual test execution.
Verify and repair the Week 13 scope; complete the SA7 evidence index, README and reproducible demo instructions.
STOP after Week 13. Do not automatically proceed to Week 14 even if time or tools remain.
Verification commands and honesty
Run the applicable checks and record actual results: flutter analyze, flutter test, flutter build web, pytest, Alembic upgrade on a disposable MySQL database, API smoke tests, and (where tooling permits) browser demonstration and screenshots. Verify both transient and permanent failure outcomes and the absence of duplicate notifications. Tests may be narrower than the later formal Week 15 campaign, but they must be sufficient to substantiate every Week 13 claim.
Never mark a test PASS unless it ran and passed. Never invent screenshots, user testing, grade outcomes, deployment results, GitHub pushes or instructor approval. If MySQL, SDKs or the browser are unavailable, complete only what can be done safely, record exactly what is NOT RUN or BLOCKED, and state how to reproduce it in a suitable environment.
Final Week 13 report and stop condition
Finish with an SA7 / Week 13 implementation report, not a complete Weeks 13–18 report. Include:
Working Week 13 capabilities and which listed screens are functional.
Files changed, migrations created, required test data, and actual commands executed.
Verification matrix of PASS / FAIL / NOT RUN with evidence paths.
Activity 1 and Activity 2 evidence locations, results and remaining issues.
One successful automation, transient recovery, permanent failure routing and safe manual handling outcomes.
Clear known defects and environment or approval blockers.
Exact local demo/run instructions and the most recent verified repository state.
Explicit statement that Weeks 14–18 are not implemented or assessed by this assignment.
Once all feasible Week 13 work is complete and the report is recorded, stop. Wait for a new Week 14 request; do not silently begin later milestones.
