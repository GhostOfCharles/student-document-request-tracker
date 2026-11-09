# Implemented Week 13 API contract

Base path /api/v1. JSON input models reject unknown properties. Sessions are opaque server-managed cookies; all state-changing calls require an allowed Origin, binding cookie and signed X-CSRF-Token. GET /auth/csrf returns the token; login renews binding, so fetch a fresh token after login. Session cookie is HttpOnly, SameSite=Lax, absolute 8 hours or 30 days for remember_me, Secure except explicit local HTTP development.

The generated docs/api-openapi.json contains executable request models, methods and query parameters. Live Swagger is /docs. Source authority: project DOCX Chapter 6; this file describes only implemented operations.

| Methods and paths | Inputs and results |
| --- | --- |
| GET /auth/csrf; POST /auth/login; GET /auth/me; POST /auth/logout | csrf_token/expires_at; login/password/remember_me → User; own User; revoke cookie/session → 204 |
| GET /services; GET /services/{id} | Active published service cards and full version/ordered requirements/options; pagination, q and category |
| POST /requests | Submission example below → 201 creation result; identical UUID/canonical payload replay → 200 original result |
| GET /requests; GET /requests/{id} | Scoped summaries with pagination/filters; detail with pinned service, current revision, payment outcome and open correction |
| GET /requests/{id}/history; GET /requests/{id}/revisions; GET /requests/{id}/revisions/{number} | Ascending history/revisions; immutable typed answers, attachment descriptors and payment evidence |
| POST /requests/{id}/correction-submissions | UUID, expected_row_version, correction_round_id, full answers/attachments/payment snapshot; only target elements may differ → 201 new revision, replay → 200 |
| POST /requests/{id}/cancel; POST /requests/{id}/acknowledge | expected_row_version plus reason, or confirm_received=true → 200 validated status result |
| POST /staff/requests/{id}/begin-review | expected_row_version, optional public_remarks → under_review |
| POST /staff/requests/{id}/payment-reviews | expected_row_version, current revision_id, outcome, conditional review_note → 201 review; status unchanged |
| POST /staff/requests/{id}/corrections | expected_row_version, general_instructions, nonempty items with target_kind/requirement_id/instruction → 201 correction round and needs_correction |
| POST /staff/requests/{id}/approve | VersionedAction plus confirm_requirements_valid=true → processing; current payment must be verified |
| POST /staff/requests/{id}/reject | expected_row_version and reason → rejected |
| POST /staff/requests/{id}/ready-for-release; POST /staff/requests/{id}/release | VersionedAction plus confirm_prepared=true or confirm_handover=true → ready_for_release or released |
| GET /requests/{id}/notes; POST /staff/requests/{id}/notes | Scoped note list; visibility and note_body → 201 append-only note, no progress reset |
| POST /files/staging; GET /files/{id}; DELETE /files/staging/{id} | Multipart file → 201 metadata; authorized binary stream with disposition; unreferenced owner staging deletion → 204 |
| GET /dashboard | Role-appropriate real counts, recent requests, unread count and staff failure count |
| GET /notifications; PATCH /notifications/{id}/read; POST /notifications/read-all | Recipient list with state filter; idempotent read timestamp; updated_count |
| GET /staff/reports/daily; POST /staff/reports/daily/regenerate | Local date query/default today → stored snapshot or SUMMARY_NOT_GENERATED; current date JSON → regenerated snapshot and automation_run_id |
| GET /staff/alerts; GET /staff/automation/runs; GET /staff/automation/jobs | Paginated/filterable safe records; open alerts by default |
| GET /staff/automation/jobs/{id}; POST .../{id}/retry; POST .../{id}/resolve | Safe details and ordered attempts; reason for allowlisted failed retry; resolution_note for failed manual handling |
| GET /staff/audit-logs | Staff-only sanitized append-only activity with pagination and event filters |

Lists return {items,page,page_size,total}, default 1/20, cap 100. UTC timestamps end in Z. Money is a decimal string. Students receive no internal notes, storage keys, worker identifiers or passwords. Another student's record is 404; wrong role is 403; missing/expired/revoked session is 401.

Example submission (substitute IDs from GET /services/{id}; no hardcoded IDs in Flutter):

~~~json
{
  "client_submission_key": "7dd20fc0-94d8-475e-9ce7-bccfc8a847d3",
  "service_id": 1,
  "service_version_id": 1,
  "answers": [
    {"requirement_id": 1, "text_value": "Synthetic scholarship purpose"},
    {"requirement_id": 2, "selected_option_id": 1},
    {"requirement_id": 4, "boolean_value": true}
  ],
  "attachments": []
}
~~~

A paid service additionally supplies payment.reference and payment.receipt_file_id according to version flags; required file fields use attachments with requirement_id/stored_file_id. One file cannot occupy two slots. Non-target correction values are preserved. Canonicalization trims normalized text, sorts arrays by requirement_id, excludes the client key and expected row version, then hashes validated business values with SHA-256. Initial and correction retries return the original creation state even after later workflow changes.

Errors use {code,detail,field_errors,trace_id}; no SQL, file path or secret is returned. Important statuses: 201 new resource; 200 read/action/replay; 204 logout/deletion; 401 authentication/credentials; 403 permission/CSRF; 404 inaccessible resource/missing summary; 409 workflow/concurrency/idempotency/payment; 413 file size; 415 file type; 422 validation; 429 login throttling with Retry-After; 500 safe internal failure; 503 database unavailable.

## Week 14 development additions

All state-changing routes require the existing CSRF and origin checks. Public registration is restricted to development and test: student-number ownership is not verified. Recovery by email or SMS is not implemented.

| Methods and paths | Inputs and results |
| --- | --- |
| POST /auth/register | full_name, student_number, email, optional phone_number, password, password_confirmation, terms_accepted=true → 201 student; no automatic login; 409 duplicate; 429 rate limit |
| PATCH /account/me; POST /account/password | email/phone update → 200 identity; current/new/confirmation password → 204, revoke all sessions |
| GET /staff/services; GET /staff/services/{id} | Staff-only service identities and published version history; draft contents excluded |
| POST /staff/services | Manager-only service_code and complete configuration → 201 inactive identity plus draft |
| GET /staff/services/{id}/draft; POST /staff/services/{id}/draft | Manager-only current draft, or clone current publication into one new editable draft |
| PUT /staff/services/{id}/draft | Manager-only expected_row_version and complete configuration → saved draft with incremented row version |
| POST /staff/services/{id}/publish | Manager-only expected_row_version and optional activate → immutable publication and current pointer |
| PATCH /staff/services/{id}/availability | Manager-only is_active and expected_current_version_id; activation requires a publication |

The configuration contains name, description, category, eligibility_instructions, processing_days, payment and ordered requirements. Each requirement uses field_key, label, optional help_text, field_type, required, type-specific validation, and ordered select options. Draft requirement IDs may change on save because no submission references an editable draft. Pinned published IDs and submitted revisions are never replaced. Publishing an active version queues one deduplicated announcement per active student.
