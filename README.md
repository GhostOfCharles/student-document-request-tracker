# Student Document Request Tracker

A full-stack, enterprise-grade university document request and tracking platform designed for students and registrar personnel. Built with **Flutter Web**, **FastAPI**, and **MySQL 8.4**.

---

## Architecture Overview

* **Frontend**: Flutter Web (Material Design 3 with custom design system, responsive layouts for desktop and mobile, reactive state management).
* **Backend**: Python FastAPI (modular routers, Pydantic validation schemas, SQLAlchemy ORM, PyMySQL).
* **Database**: MySQL 8.4+ (InnoDB, UTF8mb4, database triggers for immutable published versions and requirements, foreign key constraints).
* **Automation**: Dedicated background scheduler powered by APScheduler, with durable jobs, exponential retry policies, aging request alerts, and daily summary generators.
* **Security**: Argon2id password hashing, server-managed opaque sessions with HttpOnly same-site cookies, CSRF token validation, and private file storage outside static web roots.

---

## Core Capabilities

1. **Student Self-Service Portal**
   * Catalog of university document services (Certificates of Enrollment, Good Moral, Transcript of Records, etc.).
   * Dynamic requirement forms supporting text, dropdowns, dates, checkboxes, and file attachments (PDF/JPEG/PNG up to 5 MB).
   * Request tracking timeline with status badges, revision history, correction requests, and handover confirmation.
   * Student account registration and profile management.

2. **Registrar Staff Console**
   * Real-time request queues filtered by status, priority, and date.
   * Revision review and multi-point correction requests (students can resubmit only the affected requirements while preserving historical evidence).
   * Payment verification for fee-based documents.
   * Service Management Draft Editor: create, preview, edit, and publish new document service configurations with customized dynamic fields.
   * Staff automation dashboard: inspect background jobs, retry attempts, aging alerts, and system health summaries.

---

## Prerequisites

* **Flutter SDK**: 3.47.0 or newer (with Dart 3.13+)
* **Python**: 3.11 or newer (Python 3.12 recommended)
* **MySQL**: 8.0.16 or newer (MySQL 8.4 recommended, with `log_bin_trust_function_creators = 1`)
* **Browser**: Google Chrome or Microsoft Edge

---

## Setup & Installation

### 1. Database Configuration

Create the main and test databases in MySQL:

```sql
CREATE DATABASE sdrt CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE sdrt_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE USER 'sdrt'@'127.0.0.1' IDENTIFIED BY 'YOUR_LOCAL_PASSWORD';
GRANT ALL PRIVILEGES ON sdrt.* TO 'sdrt'@'127.0.0.1';
GRANT ALL PRIVILEGES ON sdrt_test.* TO 'sdrt'@'127.0.0.1';
FLUSH PRIVILEGES;
```

### 2. Environment Variables

Create `.env` at the root of `student_document_request_tracker`:

```env
SDRT_DATABASE_URL=mysql+pymysql://sdrt:YOUR_LOCAL_PASSWORD@127.0.0.1:3306/sdrt?charset=utf8mb4
SDRT_TEST_DATABASE_URL=mysql+pymysql://sdrt:YOUR_LOCAL_PASSWORD@127.0.0.1:3306/sdrt_test?charset=utf8mb4
SDRT_CSRF_SECRET=choose-a-random-secret-key-at-least-32-chars-long
SDRT_ENVIRONMENT=development
SDRT_SECURE_COOKIES=false
SDRT_ALLOWED_ORIGINS=["http://localhost:8000","http://127.0.0.1:8000","http://localhost:5173"]
SDRT_PRIVATE_DIR=.private/uploads
SDRT_SEED_PASSWORD=YourSecureDevPassword123!
```

### 3. Backend Dependencies & Database Migrations

From `student_document_request_tracker`:

```powershell
# Create and activate virtual environment
python -m venv backend/.venv
& backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.lock.txt

# Run migrations and seed default services and accounts
$env:PYTHONPATH = 'backend'
& backend/.venv/Scripts/python.exe -m alembic -c backend/alembic.ini upgrade head
& backend/.venv/Scripts/python.exe -m app.seed
& backend/.venv/Scripts/python.exe -m app.provision_week14_demo
```

### 4. Flutter Setup

```powershell
flutter pub get
flutter build web --no-wasm-dry-run
```

---

## Running the Application

### Option A: VS Code (F5 Launch)
Open the workspace in VS Code and press **F5** or select one of the launch configurations:
* **Full Stack (Backend + Flutter Chrome)**
* **FastAPI Backend (Port 8000)**
* **Flutter Web (Chrome - Hot Reload)**
* **FastAPI Scheduler**

### Option B: Terminal

#### Terminal 1 — Backend API
```powershell
cd student_document_request_tracker
$env:PYTHONPATH = 'backend'
& backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
* **Web App**: [http://localhost:8000](http://localhost:8000)
* **Swagger API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

#### Terminal 2 — Flutter Web (Hot Reload Development)
```powershell
cd student_document_request_tracker
flutter run -d chrome --web-port 5173 --dart-define=API_BASE=http://localhost:8000/api/v1
```

#### Terminal 3 — Background Automation Scheduler (Optional)
```powershell
cd student_document_request_tracker
$env:PYTHONPATH = 'backend'
& backend/.venv/Scripts/python.exe -m app.automation.scheduler
```

---

## Default Development Accounts

All seed accounts use the password specified by `SDRT_SEED_PASSWORD` in `.env`:

| Role | Identifier / Email | Description |
|---|---|---|
| **Student** | `TEST-001` or `student@example.test` | Default student account (Juan Dela Cruz) |
| **Student** | `TEST-002` or `other@example.test` | Secondary student account (Maria Santos) |
| **Staff** | `registrar@example.test` | University registrar with service management permissions |

---

## Testing & Quality Assurance

Run the test suite from `student_document_request_tracker`:

```powershell
# 1. Flutter widget & unit tests
flutter test

# 2. Backend pytest test suite
$env:PYTHONPATH = 'backend'
& backend/.venv/Scripts/python.exe -m pytest backend/tests

# 3. Live end-to-end API smoke test (with backend running)
& backend/.venv/Scripts/python.exe scripts/api_smoke.py
```
