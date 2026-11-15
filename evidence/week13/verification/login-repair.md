# Local login repair — 31 October 2026 (Asia/Manila)

The workstation configuration was changed to Laragon MySQL on port 3306 after the original API process had started. That process retained its previously loaded database settings. The current `.env` password matched the seeded Laragon student account, while login through the existing API returned HTTP 401 `INVALID_CREDENTIALS`.

The old API was gracefully stopped through its original execution session and restarted with the current `.env`. No databases were dropped, passwords changed, or accounts reseeded during this repair. The new API accepted the student login, authenticated `/auth/me`, and loaded `/dashboard`, each returning HTTP 200.

The Flutter UI previously replaced every 401 error with a session-expiry message. It now uses that message only for `AUTHENTICATION_REQUIRED`; invalid credentials retain the server's actual explanation.

Actual checks:

| Check / command | Result |
| --- | --- |
| `flutter analyze` | PASS — no issues |
| `flutter test` | PASS — 5 tests, including incorrect-login message regression |
| `flutter build web --no-wasm-dry-run` | PASS — rebuilt `build/web` |
| `backend/.venv/Scripts/python.exe scripts/login_smoke.py` | PASS — rejected incorrect password shows credential error, student and registrar authenticate through Flutter in Edge |

Browser results are in [login-repair.json](login-repair.json). Actual authenticated captures are [student](../screenshots/login-repair-student.png) and [registrar](../screenshots/login-repair-staff.png). Browser automation reads the local seed password without printing it and records no passwords, session tokens, or CSRF values. Earlier acceptance records remain historical records of their original environment.

To reproduce, use the current local MySQL instance and `.env`, start FastAPI on port 8000, then run the login smoke script from repository root. Restart API and scheduler processes whenever their configuration changes. The seed command intentionally preserves existing passwords; editing `SDRT_SEED_PASSWORD` alone does not reset an already seeded account.

This is a Week 13 login/setup repair. No later milestone was implemented or assessed.
