#!/usr/bin/env bash
# ==============================================================================
# NOOP Home Lab — PostgreSQL Automated Backup Script
# Creates a compressed pg_dump and manages retention.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOMELAB_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${HOMELAB_DIR}/backups"
RETENTION_DAYS=30

mkdir -p "${BACKUP_DIR}"

TIMESTAMP="$(date -u +"%Y%m%d_%H%M%SZ")"
BACKUP_FILE="${BACKUP_DIR}/noop_backup_${TIMESTAMP}.sql.gz"

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Starting NOOP database backup..."

# Source .env if present
if [[ -f "${HOMELAB_DIR}/.env" ]]; then
    set -a
    source "${HOMELAB_DIR}/.env"
    set +a
fi

DB_USER="${POSTGRES_USER:-noop}"
DB_NAME="${POSTGRES_DB:-noop_homelab}"

# Run pg_dump inside the postgres container
if ! docker compose -f "${HOMELAB_DIR}/docker-compose.yml" exec -T postgres \
    pg_dump -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists | gzip > "${BACKUP_FILE}"; then
    echo "ERROR: pg_dump failed!" >&2
    rm -f "${BACKUP_FILE}"
    exit 1
fi

# Verification: Check file size > 0
FILE_SIZE=$(stat -c%s "${BACKUP_FILE}" 2>/dev/null || stat -f%z "${BACKUP_FILE}" 2>/dev/null || echo 0)
if [[ "${FILE_SIZE}" -le 50 ]]; then
    echo "ERROR: Backup file ${BACKUP_FILE} is suspiciously small (${FILE_SIZE} bytes)!" >&2
    rm -f "${BACKUP_FILE}"
    exit 1
fi

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Backup successful: ${BACKUP_FILE} (${FILE_SIZE} bytes)"

# Enforce retention policy
echo "Cleaning backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "noop_backup_*.sql.gz" -type f -mtime +"${RETENTION_DAYS}" -exec rm -v {} \;

echo "Backup process completed successfully."
