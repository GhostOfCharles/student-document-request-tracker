# Deployment & Operations Runbook (`deploy/`)

This directory contains the production Linux deployment templates for **Student Document Request Tracker (SDRT)**, matching the Section 13 reference topology in [docs/specification/project-extracted.txt](../docs/specification/project-extracted.txt).

## Contents

| File | Purpose |
|---|---|
| `nginx.conf` | HTTPS reverse proxy, Flutter Web static serving with SPA fallback, `/api/` proxy to Uvicorn, security headers, and `.private` denial. |
| `sdrt-api.service` | `systemd` service unit for FastAPI (`uvicorn app.main:app`) running as least-privileged user `sdrt` on `127.0.0.1:8000`. |
| `sdrt-scheduler.service` | `systemd` service unit for the single designated APScheduler worker (`python -m app.automation.scheduler`) with `Restart=always`. |
| `.env.production.example` | Secret-free template for `/etc/sdrt/sdrt.env`. |
| `backup.sh` | Paired MySQL (`--single-transaction --triggers --routines`) + private uploads backup script with SHA-256 manifests and 7-day rolling retention. |

## Linux VPS Provisioning Checklist

1. **System User & Private Storage**
   ```bash
   sudo useradd --system --home /opt/sdrt --shell /usr/sbin/nologin sdrt
   sudo mkdir -p /opt/sdrt/app /var/lib/sdrt/private_uploads /etc/sdrt /var/backups/sdrt
   sudo chown -R sdrt:sdrt /opt/sdrt /var/lib/sdrt
   sudo chmod 700 /var/lib/sdrt/private_uploads
   ```
2. **MySQL Least-Privileged Account**
   ```sql
   CREATE DATABASE sdrt CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'sdrt_app'@'127.0.0.1' IDENTIFIED BY 'STRONG_RANDOM_PASSWORD';
   GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES, TRIGGER ON sdrt.* TO 'sdrt_app'@'127.0.0.1';
   FLUSH PRIVILEGES;
   ```
   *(Ensure `log_bin_trust_function_creators = 1` or `SUPER`/`SYSTEM_USER` only during migrations if binary logging is active.)*
3. **Application & Migrations**
   - Install pinned Python dependencies: `python -m pip install -r backend/requirements.lock.txt`
   - Build Flutter Web release bundle: `flutter build web --release`
   - Apply Alembic migrations: `PYTHONPATH=backend python -m alembic -c backend/alembic.ini upgrade head`
4. **Services & TLS**
   - Install `/etc/sdrt/sdrt.env` (`chmod 600`, owned by `sdrt:sdrt`)
   - Copy `sdrt-api.service` and `sdrt-scheduler.service` to `/etc/systemd/system/`
   - Enable & start: `sudo systemctl enable --now sdrt-api sdrt-scheduler`
   - Install `nginx.conf` to `/etc/nginx/sites-available/sdrt`, obtain Let's Encrypt cert via `certbot --nginx`, and reload Nginx.

## Recovery Procedure

1. Stop `sdrt-scheduler` and `sdrt-api` (or block writes) before incompatible restore.
2. Restore MySQL dump (`gunzip -c db_sdrt.sql.gz | mysql sdrt`) and extract matching `private_uploads.tar.gz` into `PRIVATE_DIR`.
3. Verify `sha256sum -c private_uploads.sha256`, trigger count (`SHOW TRIGGERS`), and active `alembic_version`.
4. Start `sdrt-api`, verify smoke checks, then start `sdrt-scheduler` so `recover()` reconciles any interrupted leases.
