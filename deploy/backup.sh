#!/usr/bin/env bash
# Paired daily backup script for MySQL (sdrt) and private evidence storage
# Implements Section 13 Backup and Recovery policy (7-day rolling retention).
set -euo pipefail

BACKUP_ROOT="${BACKUP_ROOT:-/var/backups/sdrt}"
PRIVATE_DIR="${PRIVATE_DIR:-/var/lib/sdrt/private_uploads}"
DB_NAME="${DB_NAME:-sdrt}"
MYSQL_DEFAULTS="${MYSQL_DEFAULTS:-/etc/sdrt/mysql-backup.cnf}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TARGET_DIR="${BACKUP_ROOT}/${STAMP}"
mkdir -p "${TARGET_DIR}"
chmod 700 "${TARGET_DIR}"

echo "[$(date -u +%FT%TZ)] Starting paired backup in ${TARGET_DIR}"

# 1. Consistent InnoDB dump including triggers and routines
mysqldump --defaults-extra-file="${MYSQL_DEFAULTS}" \
  --single-transaction --routines --triggers --hex-blob \
  "${DB_NAME}" | gzip -9 > "${TARGET_DIR}/db_${DB_NAME}.sql.gz"

# 2. Private uploads archive + SHA-256 manifest
if [[ -d "${PRIVATE_DIR}" ]]; then
  tar -C "${PRIVATE_DIR}" -czf "${TARGET_DIR}/private_uploads.tar.gz" .
  (cd "${PRIVATE_DIR}" && find . -type f -exec sha256sum {} + | sort) > "${TARGET_DIR}/private_uploads.sha256"
else
  echo "ERROR: Private uploads directory not found: ${PRIVATE_DIR}" >&2
  exit 1
fi

# 3. Backup archive integrity manifest
(cd "${TARGET_DIR}" && sha256sum db_${DB_NAME}.sql.gz private_uploads.tar.gz > backup.sha256)

# 4. Enforce 7-day rolling retention
find "${BACKUP_ROOT}" -mindepth 1 -maxdepth 1 -type d -mtime +"${RETENTION_DAYS}" -exec rm -rf {} +

echo "[$(date -u +%FT%TZ)] Paired backup complete. Copy ${TARGET_DIR} off-host for disaster recovery."
