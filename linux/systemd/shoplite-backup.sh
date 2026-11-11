#!/usr/bin/env bash
# ShopLite Automated Nightly PostgreSQL Database Backup Script
set -euo pipefail

BACKUP_DIR="/var/backups/shoplite"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/shoplite_db_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=7

# Ensure backup destination directory exists with secure permissions
mkdir -p "${BACKUP_DIR}"
chmod 700 "${BACKUP_DIR}"

echo "[$(date -Iseconds)] Initiating PostgreSQL database backup..."

# Execute pg_dump inside running postgres container and stream through gzip
if docker exec -t shoplite-postgres pg_dump -U shoplite_user -d shoplite_db | gzip > "${BACKUP_FILE}"; then
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo "[$(date -Iseconds)] Backup completed successfully: ${BACKUP_FILE} (${BACKUP_SIZE})"
    chmod 600 "${BACKUP_FILE}"
else
    echo "[$(date -Iseconds)] ERROR: pg_dump failed!" >&2
    rm -f "${BACKUP_FILE}"
    exit 1
fi

# Rotate backups older than retention window
echo "[$(date -Iseconds)] Pruning local backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -type f -name "shoplite_db_*.sql.gz" -mtime +"${RETENTION_DAYS}" -delete

echo "[$(date -Iseconds)] Backup routine finished."
exit 0
