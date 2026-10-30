# Activity 2 verification and improvement

The bounded task is creation of an authorized in-app notification. Tests execute real FastAPI calls, SQLAlchemy transactions, MySQL constraints, worker claims and notification inserts. They use a dedicated disposable sdrt_test database with synthetic users/files. No production timer was shortened and no failure-injection HTTP endpoint exists.

Exact reproduction from repository root:

~~~powershell
$env:PYTHONPATH = 'backend'
& backend/.venv/Scripts/python.exe -m pytest backend/tests -v -s --tb=short
~~~

The fixture requires SDRT_TEST_DATABASE_URL to use MySQL and end in _test, rebuilds that schema through Alembic, and seeds controlled accounts. Failure flags are internal safe test metadata honored only when SDRT_ENVIRONMENT=test. The latest raw outcome is 13 passed in logs/pytest.log. Logs/automation-tests.jsonl contains real JSON events, and observed-jobs.json is queried from MySQL after assertions.

| Experiment | Expected | Observed |
| --- | --- | --- |
| Ordinary status task | One notification and succeeded job/attempt | Actual status deliveries succeed; worker commits notification and finalization together |
| Transient test fault | First failure leaves durable pending work; retry succeeds | Job 40: transient_failure then succeeded at attempt 2, one recipient/event notification |
| Permanent invalid-configuration test fault | Stop immediately and expose to authorized staff | Job 41: permanent_failure at attempt 1; monitoring API includes it; student denied 403; registrar resolution records resolved_manually |
| Repeated transient fault | Automatic ceiling of three; no endless loop | Job 42 stops failed_permanently at 3, remains stopped despite future process calls; two audited manual cycles stop again at 6 and 9; cycle three rejected 409 |
| Interrupted worker | Preserve attempt, expire lease, reclaim without duplicate delivery | Job 43: attempt 1 interrupted, attempt 2 succeeded; exactly one notification; stale original finalizer rejected |
| Unauthorized recipient | No cross-owner notification | Separate acceptance test records RECIPIENT_UNAUTHORIZED and a bounded staff-only failure notice |
| Human handling through Flutter | Display actual failure and attempts; no further retry at nine | browser-failure-monitor.json and screenshots show staff viewing job 42, no Retry safely control at ceiling, and an HTTP-confirmed manual resolution |

Clock integrity: structured event timestamp is the actual UTC logging time. Failure tests supply explicit controlled UTC now values for eligibility/lease decisions. Attempt times can therefore be later than the wall-clock test run, including the two simulated manual cycles on following days. This is a clock-controlled demonstration, not evidence that a host ran continuously for those dates. The first automatic backoffs are checked at +1 and +6 minutes, corresponding to one then five minutes. Production schedules remain one minute/15 minutes/17:00/02:00.

The browser monitor demonstration runs after pytest using the populated test database on a separate API origin. Start it and then the capture in separate root terminals:

~~~powershell
& backend/.venv/Scripts/python.exe scripts/test_server.py
& backend/.venv/Scripts/python.exe scripts/monitor_failure_demo.py
~~~

It is a real staff session, a real failed-job query, an actual Flutter dialog and an actual resolve endpoint. It changes job 42 from the failed state captured in observed-jobs.json to resolved_manually. Those files are successive snapshots, not contradictory simultaneous states. Rerunning the monitor demonstration requires rerunning pytest first because resolved jobs are intentionally not eligible for another resolution.

Duplicate protection was observed through exact recipient/event counts after retry and interruption, repeated scan deduplication, concurrent initial-submission replay and single immutable revision creation. MySQL unique constraints back the application checks. Endless retries were prevented by retained attempt_count, durable terminal status, increasing ceilings 3/6/9 and rejection of a third manual cycle. Silent loss was prevented by durable intent committed with the business event, retained attempts/errors, and direct monitoring visibility independent of notification delivery.

Improvement evidence: initial tests found an unclosed named-lock/transaction boundary, a read_at response mismatch, and a general response middleware that replaced the file route's private cache directive. These were repaired and reverified. Earlier failure logs remain under logs/pytest-second.log and logs/pytest-edge-before-fix.log. Initial Flutter checks found the installed file-picker API had changed; code was adapted to the actual package. Browser harness corrections waited for actual HTTP completion, used actual accessible roles and avoided duplicate live-region text matches. Preliminary browser logs are retained as debugging evidence, not counted as acceptance PASS.

Interpretation: the experiment supports bounded local recovery and absence of duplicates in the exercised cases. It does not establish every possible crash ordering, physical database durability under power loss, production availability or real staff usability. A permanently failed notification is visible even if a failure notice cannot be delivered; direct T09 querying is the independent recovery path. Operational staff must still investigate and explain manual handling. No actual user acceptance or instructor approval is asserted.
