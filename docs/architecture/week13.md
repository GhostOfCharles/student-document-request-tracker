# Week 13 architecture and workflow

The local demonstration uses synthetic users and documents. The browser, API, database, private storage and separate scheduler are real processes. Instructor approval is external and unverified.

~~~mermaid
flowchart LR
  B[Flutter Web browser] -->|same origin HTTPS or local HTTP; session cookie and CSRF| A[FastAPI]
  A -->|SQLAlchemy and PyMySQL transaction| D[(MySQL InnoDB)]
  A -->|authorized upload and download| F[Private evidence directory]
  W[One APScheduler 3.x process] -->|claim leases and durable attempts| D
  W -->|expire unused staging evidence| F
  D -->|notifications and monitoring queries| A
~~~

The browser is untrusted. It never chooses an owner, payment amount, status, timestamp or role. FastAPI authorizes every operation. Files are outside static web assets and no storage key is returned. MySQL is the transaction boundary for a business change, history, audit and queued status jobs. File upload is staged before request submission; unused staging expires after 24 hours.

~~~mermaid
stateDiagram-v2
  [*] --> submitted: validated initial revision
  submitted --> under_review: staff begins review
  submitted --> cancelled: owner gives reason
  under_review --> cancelled: owner gives reason
  under_review --> needs_correction: staff specifies targets
  needs_correction --> under_review: owner submits immutable new revision
  under_review --> rejected: staff gives reason
  under_review --> processing: staff confirms requirements; latest payment verified if needed
  processing --> ready_for_release: staff confirms prepared
  ready_for_release --> released: staff confirms actual handover
  released --> completed: owner acknowledges receipt
~~~

Payment reviews never independently advance status. Correction pauses staff delay alerts and extends the due date by the correction interval exactly once. Published versions remain pinned even if a service identity is later deactivated. Students can inspect previous evidence but cannot rewrite it.

~~~mermaid
flowchart TD
  E[API business event] --> T[Atomic business record and pending outbox job]
  T --> C[Worker claims row and records attempt with 120 second lease]
  C --> S{Bounded delivery result}
  S -->|success| N[Notification plus succeeded job and attempt commit together]
  S -->|transient| R[Pending with 1 minute then 5 minute backoff]
  R --> C
  S -->|permanent or exhausted| H[failed_permanently visible directly to staff]
  H --> M{Authorized human decision}
  M -->|allowlisted retry with reason| R
  M -->|resolution note| X[resolved_manually; delivery not asserted]
  C -->|process interruption| L[Expired lease marks interrupted attempt]
  L -->|budget remains| R
  L -->|budget exhausted| H
  P[15 minute aging and stalled scan] --> T
  Q[17:00 Asia/Manila summary] --> D[Unique local-date consistent snapshot and run log]
~~~

Notifications use unique recipient/event keys, jobs use unique idempotency keys, requests/revisions use UUID keys and canonical SHA-256 payload hashes. Stale staff row versions fail with 409. Claims use MySQL row locks and SKIP LOCKED. A stale worker cannot finalize a reclaimed lease. Cleanup marks removed metadata first, then retries byte deletion on later scans.

The designated scheduler holds a process-lifetime MySQL named lock; a second instance exits. Scheduled IDs are explicit, coalesced and max_instances=1. Startup processes pending work, recovers expired leases and abandoned runs, scans aging and cleanup, and generates a delayed current-date summary only if local time is already 17:00 or later. It does not manufacture past-day snapshots.

