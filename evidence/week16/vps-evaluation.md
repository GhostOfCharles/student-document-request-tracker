# Week 16 VPS Hosting & Deployment Evaluation

**Date**: 17 November 2026  
**Project**: Student Document Request Tracker (SDRT)  
**Milestone**: Week 16 — Hosting Evaluation & Test Environment Deployment  
**Reference Specification**: `docs/specification/project-extracted.txt` (Section 13: *Deployment and operational handover*)

---

## 1. Architectural Constraints Driving Hosting Selection

The Student Document Request Tracker is not a stateless web app. Any candidate hosting platform must satisfy **five mandatory runtime requirements**:

| Requirement | Technical Reason in Codebase |
|---|---|
| **1. Persistent Python App Process** | `uvicorn app.main:app` serves `/api/v1/*`, manages Argon2id authentication (`backend/app/auth.py`), and enforces CSRF/origin validation. |
| **2. Dedicated Persistent Background Worker** | `python -m app.automation.scheduler` runs `BlockingScheduler` as a **single designated process** holding a MySQL session lock (`GET_LOCK('sdrt_designated_scheduler', 0)`), polling durable `automation_jobs` every 1 minute, scanning overdue/stalled requests every 15 minutes, and generating daily summaries at 17:00 `Asia/Manila`. |
| **3. MySQL 8.0.16+ / 8.4 with Triggers** | Schema relies on 23 domain tables (`alembic` revision `0002_published_children`), InnoDB `READ COMMITTED` row locks, and **22 MySQL `BEFORE UPDATE` / `BEFORE DELETE` immutability triggers** (requiring `log_bin_trust_function_creators = 1` or migration-time privileges). |
| **4. Private Durable Filesystem Storage** | Uploaded PDF/JPEG/PNG files are validated by `file_validation.py` and written outside static web assets (`SDRT_PRIVATE_DIR`), served solely via authorized `/api/v1/files/{file_id}` responses with SHA-256 verification. Ephemeral container filesystems wipe uploaded evidence on restart. |
| **5. HTTPS Reverse Proxy & Same-Origin Routing** | Nginx terminates TLS 1.2/1.3, serves the Flutter Web release bundle (`build/web`) with SPA fallback at `/`, forwards `/api/` to FastAPI (preserving API `404` for unknown `/api/*` routes), and enables `SDRT_SECURE_COOKIES=true`. |

---

## 2. Why Serverless & Standard Free PaaS Tiers Fail

Standard free PaaS/serverless platforms (**Vercel**, **Netlify**, **Render Free Web Service**, **Heroku Eco**) are **architecturally incompatible** with SDRT without major redesign:

* **Auto-Sleep / Cold Starts**: Free PaaS web services spin down after ~15 minutes of HTTP inactivity, halting or killing `apscheduler` and breaking the 15-minute aging scan and 17:00 `Asia/Manila` cron summary.
* **Ephemeral Filesystems**: Container restarts or redeploys discard local disks, destroying `.private/uploads` even though `stored_files` metadata remains in MySQL.
* **No Co-Located MySQL 8.4 with Trigger Privileges**: Managed free-tier databases often disable custom MySQL triggers, substitute PostgreSQL, or impose strict connection/row limits incompatible with `alembic` migrations.

---

## 3. Candidate VPS Provider Comparison

| Evaluation Criterion | **Hostinger VPS (KVM 1)** *(Spec Reference Candidate)* | **Oracle Cloud "Always Free" (ARM Ampere A1 / AMD)** | **AWS Free Tier (EC2 `t2.micro` / `t3.micro`)** | **GitHub Student Pack (DigitalOcean / Azure Credits)** |
|---|---|---|---|---|
| **Cost (Academic / Test)** | Paid (~US\$4.99–\$5.99/mo promo; no free tier) | **\$0 / month** (Always Free tier, card verification only) | **\$0 / month** for first 12 months (750 hrs/mo) | **\$0** using \$200 DigitalOcean / \$100 Azure student credit |
| **Compute & RAM** | 1 vCPU, 4 GB RAM, 50 GB NVMe | Up to 4 OCPUs, 24 GB RAM (ARM) or 2x 1 GB RAM (AMD) | 1–2 vCPU, **1 GB RAM**, 30 GB EBS | 1–2 vCPU, 1–2 GB RAM Droplet/VM |
| **Persistent Python + `systemd`** | Full root Ubuntu 24.04; supports `sdrt-api` + `sdrt-scheduler` | Full root Ubuntu 24.04; supports both `systemd` units | Full root Ubuntu 24.04; tight on 1 GB RAM without swap | Full root Ubuntu 24.04; supports both `systemd` units |
| **MySQL 8.0 / 8.4 + Triggers** | Full local `mysql-server-8.0+` or 8.4 control | Full local MySQL 8.x or HeatWave control | Full local MySQL 8.x (recommended to configure 1–2 GB swap) | Full local MySQL 8.x or managed DB |
| **Private Persistent Disk** | 50 GB NVMe block storage | Up to 200 GB persistent block volume | 30 GB EBS gp2/gp3 persistent volume | 25–50 GB SSD persistent volume |
| **HTTPS / Reverse Proxy** | Nginx + Certbot (Let's Encrypt) over public IPv4 | Nginx + Certbot (requires VCN Security List ports 80/443) | Nginx + Certbot (requires Security Group ports 80/443) | Nginx + Certbot over public IPv4 |
| **Operational Risk / Notes** | Requires paid subscription; best if department already rents Hostinger | ARM capacity in some regions can be limited; AMD micro (1 GB) needs swap | 12-month expiry; 1 GB RAM is tight during `flutter build web` (build in CI instead) | Credits expire after 12 months; ideal for zero-cost academic/OJT demos |

---

## 4. Recommendation & Week 16 Test Environment Decision

1. **Production Candidate (Departmental Rollout)**: **Hostinger KVM 1 VPS** (or equivalent 2–4 GB RAM Ubuntu 24.04 LTS KVM VPS) remains the strongest low-maintenance paid target when an institution funds hosting, because 4 GB RAM comfortably hosts Nginx, FastAPI (2 Uvicorn workers), the dedicated APScheduler worker, and MySQL 8.4 with InnoDB buffer headroom.
2. **Zero-Cost Cloud Candidate (Student / Academic Rollout)**: **Oracle Cloud Always Free** (Ampere A1) or **GitHub Student Developer Pack (DigitalOcean Droplet)** provides genuine persistent disk, `systemd` supervision, and full MySQL 8 trigger support without incurring out-of-pocket costs.
3. **Week 16 Isolated Staging Execution (This Deliverable)**: Consistent with the academic milestone scope (no live paid purchase assumed prior to Week 18 handover), all Week 16 deployment artifacts (`deploy/nginx.conf`, `deploy/sdrt-api.service`, `deploy/sdrt-scheduler.service`, `deploy/backup.sh`) were authored and **verified locally against an isolated staging environment**:
   * **Reverse Proxy**: Laragon Nginx `1.30.4` listening on `http://127.0.0.1:8080`, serving the compiled `flutter build web --release` bundle at `/` with SPA fallback and proxying `/api/` to FastAPI on `127.0.0.1:8081`.
   * **Isolated Database & Storage**: Dedicated MySQL 8.4.3 schema `sdrt_staging` (24 tables including `alembic_version`, 22 immutability triggers) and isolated private directory `.private/staging_uploads`.
   * **Dedicated Scheduler Process**: Standalone `python -m app.automation.scheduler` process bound to `sdrt_staging` via `GET_LOCK('sdrt_designated_scheduler', 0)`.
