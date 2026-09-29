#!/usr/bin/env bash
# ==============================================================================
# scripts/db_backup.sh
# Performs a binary custom-format backup (pg_dump -Fc) of the PostgreSQL database.
# Works against the docker-compose 'db' container or direct local connection.
# Refuses to overwrite any existing backup file.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Load .env if present
if [[ -f "${REPO_ROOT}/.env" ]]; then
  # export variables from .env ignoring comments
  set -a
  # shellcheck source=/dev/null
  source <(grep -v '^#' "${REPO_ROOT}/.env" | sed -e 's/\r$//')
  set +a
fi

DB_USER="${POSTGRES_USER:-${DB_USER:-postgres}}"
DB_NAME="${POSTGRES_DB:-${DB_NAME:-SkillSync}}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
BACKUP_DIR="${REPO_ROOT}/backups"

mkdir -p "${BACKUP_DIR}"

TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
DEFAULT_BACKUP_FILE="${BACKUP_DIR}/worknexus_${DB_NAME}_${TIMESTAMP}.dump"
OUTPUT_FILE="${1:-${DEFAULT_BACKUP_FILE}}"

# Refuse to overwrite existing backup
if [[ -e "${OUTPUT_FILE}" ]]; then
  echo "ERROR: Backup file already exists: ${OUTPUT_FILE}" >&2
  echo "Refusing to overwrite existing backup to prevent data loss." >&2
  exit 1
fi

echo "==> Starting database backup of '${DB_NAME}'..."
echo "==> Target file: ${OUTPUT_FILE}"

# Check if docker-compose Postgres service is running
USE_DOCKER=false
if command -v docker >/dev/null 2>&1 && docker compose ps --services --filter "status=running" 2>/dev/null | grep -q "^db$"; then
  USE_DOCKER=true
fi

if [[ "${USE_DOCKER}" = true ]]; then
  echo "==> Executing pg_dump via docker compose exec db..."
  docker compose exec -T db pg_dump -U "${DB_USER}" -d "${DB_NAME}" -Fc > "${OUTPUT_FILE}"
elif command -v pg_dump >/dev/null 2>&1; then
  echo "==> Executing local pg_dump..."
  PGPASSWORD="${POSTGRES_PASSWORD:-${DB_PASSWORD:-}}" pg_dump \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    -Fc \
    -f "${OUTPUT_FILE}"
else
  echo "ERROR: Neither running docker-compose 'db' service nor local pg_dump found." >&2
  exit 1
fi

if [[ ! -s "${OUTPUT_FILE}" ]]; then
  echo "ERROR: Backup failed or produced empty file: ${OUTPUT_FILE}" >&2
  rm -f "${OUTPUT_FILE}"
  exit 1
fi

BACKUP_SIZE="$(ls -lh "${OUTPUT_FILE}" | awk '{print $5}')"
echo "==> Backup completed successfully: ${OUTPUT_FILE} (${BACKUP_SIZE})"
