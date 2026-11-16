#!/usr/bin/env bash
# ==============================================================================
# NOOP Home Lab — PostgreSQL Database Restore Script
# Restores a compressed SQL dump into the running PostgreSQL container.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOMELAB_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <path_to_backup_file.sql.gz>"
    echo "Example: $0 ${HOMELAB_DIR}/backups/noop_backup_20261116_120000Z.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

if [[ ! -f "${BACKUP_FILE}" ]]; then
    echo "ERROR: Backup file '${BACKUP_FILE}' does not exist!" >&2
    exit 1
fi

# Source .env if present
if [[ -f "${HOMELAB_DIR}/.env" ]]; then
    set -a
    source "${HOMELAB_DIR}/.env"
    set +a
fi

DB_USER="${POSTGRES_USER:-noop}"
DB_NAME="${POSTGRES_DB:-noop_homelab}"

echo "========================================================================"
echo "WARNING: Restoring will overwrite existing data in '${DB_NAME}'!"
echo "Target: ${BACKUP_FILE}"
echo "========================================================================"
read -p "Are you sure you want to proceed? (type 'yes' to confirm): " CONFIRMATION

if [[ "${CONFIRMATION}" != "yes" ]]; then
    echo "Restore cancelled."
    exit 0
fi

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Restoring database..."

if ! gzip -dc "${BACKUP_FILE}" | docker compose -f "${HOMELAB_DIR}/docker-compose.yml" exec -T postgres \
    psql -U "${DB_USER}" -d "${DB_NAME}"; then
    echo "ERROR: Restore failed!" >&2
    exit 1
fi

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Database restored successfully from ${BACKUP_FILE}."
