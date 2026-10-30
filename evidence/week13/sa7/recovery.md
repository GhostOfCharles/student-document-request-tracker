# Week 13 recovery procedure

Use synthetic development data only. An authorized registrar signs in and opens Automation. Read the job's status, safe error code and ordered attempts. The failure list comes directly from MySQL even if notifications cannot be delivered.

1. If a job is pending for a future next_attempt_at, allow its bounded automatic retry. Do not replay the original request submission or staff action to deliver a notification.
2. If a worker stopped, restore database connectivity and start exactly one worker with python -m app.automation.scheduler. Startup recovers expired 120-second leases and records interrupted attempts. Never overwrite attempt_count or delete attempts.
3. For failed_permanently, inspect the safe code and confirm the underlying cause is addressed. T09 permits retry only for the allowlisted idempotent notification handler, requires a reason, preserves all attempts, and extends max_attempts by three. At most two manual cycles are allowed (ceilings 3, 6 and 9).
4. Unsupported job types cannot be retried through the UI. Investigate configuration offline. Do not run arbitrary scripts or mutate jobs through browser payloads.
5. If manual registrar handling is appropriate, choose Record manual handling and provide a resolution note. The record becomes resolved_manually with actor and time. This does not assert that automated delivery succeeded. Completed/running/resolved jobs cannot be retried.
6. Check recipient notifications and the original request's history after recovery. Duplicate delivery is prevented by unique recipient/event keys and atomic finalization.
7. For missing private bytes, preserve metadata and historical links, stop the affected demonstration, and restore matching files from the controlled development backup. Never mark missing evidence as reviewed or replace a historical file in place.

Startup scans evaluate present state, not every missed interval. A missing current-day summary after 17:00 becomes a delayed current-state snapshot with its actual generated_at; past snapshots are never reconstructed. Expired unused uploads are marked removed before byte deletion, which is retried by cleanup. Unreferenced upload remnants are removed only after a 24-hour safety interval.

Database connection failures can prevent immediate error recording. Previously committed pending/running work and lease expiry preserve intent; safe worker logs identify dependency unavailability. Preserve the database and private files together when transferring the local demo. No production backup/restore assessment is claimed.

