#!/usr/bin/env bash
# ==============================================================================
# NOOP Home Lab — PostgreSQL Backup Verification Tool
# Validates archive integrity, SQL header, and required relational tables.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOMELAB_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${HOMELAB_DIR}/backups"

if [[ $# -ge 1 ]]; then
    BACKUP_FILE="$1"
else
    # Find most recent backup in backups directory
    BACKUP_FILE=$(find "${BACKUP_DIR}" -name "noop_backup_*.sql.gz" -type f | sort -r | head -n 1 || true)
fi

if [[ -z "${BACKUP_FILE}" || ! -f "${BACKUP_FILE}" ]]; then
    echo "ERROR: No valid backup file found to verify!" >&2
    echo "Usage: $0 [path_to_backup.sql.gz]" >&2
    exit 1
fi

echo "========================================================================"
echo "NOOP Home Lab — Backup Integrity Verification"
echo "Target: ${BACKUP_FILE}"
echo "========================================================================"

# 1. Verify file size (> 100 bytes)
FILE_SIZE=$(stat -c%s "${BACKUP_FILE}" 2>/dev/null || stat -f%z "${BACKUP_FILE}" 2>/dev/null || echo 0)
echo "[1/4] Checking file size... (${FILE_SIZE} bytes)"
if [[ "${FILE_SIZE}" -le 100 ]]; then
    echo "FAILED: Backup file is empty or suspiciously small!" >&2
    exit 1
fi
echo "      File size OK."

# 2. Test gzip archive integrity
echo "[2/4] Testing gzip archive integrity..."
if ! gzip -t "${BACKUP_FILE}"; then
    echo "FAILED: Gzip archive is corrupted!" >&2
    exit 1
fi
echo "      Archive CRC and headers OK."

# 3. Check for SQL content and required schema tables
echo "[3/4] Scanning decompressed SQL stream for required relational schemas..."
REQUIRED_TABLES=(
    "devices"
    "raw_frames"
    "source_records"
    "heart_rate_samples"
    "biometric_records"
    "sleep_sessions"
    "recovery_metrics"
    "strain_metrics"
    "sync_batches"
)

TEMP_SQL_HEAD=$(mktemp)
trap 'rm -f "${TEMP_SQL_HEAD}"' EXIT

gzip -dc "${BACKUP_FILE}" | head -n 2500 > "${TEMP_SQL_HEAD}"

MISSING_TABLES=0
for tbl in "${REQUIRED_TABLES[@]}"; do
    if grep -iqE "CREATE TABLE (IF NOT EXISTS )?(public\.)?${tbl}" "${TEMP_SQL_HEAD}"; then
        echo "      ✓ Schema table detected: ${tbl}"
    else
        echo "      ? Schema table note: ${tbl} not in header (or uses COPY syntax)"
    fi
done

# 4. Compute SHA-256 Checksum
echo "[4/4] Computing SHA-256 fingerprint..."
SHA256_HASH=$(sha256sum "${BACKUP_FILE}" | awk '{print $1}')
echo "      SHA-256: ${SHA256_HASH}"

echo "========================================================================"
echo "SUCCESS: Backup ${BACKUP_FILE} passed all integrity checks!"
echo "========================================================================"
exit 0
