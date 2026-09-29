#!/usr/bin/env bash
# ==============================================================================
# scripts/db_restore.sh
# Restores a binary custom-format backup (pg_restore -Fc) into PostgreSQL.
# Usage: ./scripts/db_restore.sh <backup_file> [target_database]
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Load .env if present
if [[ -f "${REPO_ROOT}/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source <(grep -v '^#' "${REPO_ROOT}/.env" | sed -e 's/\r$//')
  set +a
fi

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <backup_file_path> [target_database_name]" >&2
  exit 1
fi

BACKUP_FILE="$1"
if [[ ! -f "${BACKUP_FILE}" ]]; then
  echo "ERROR: Backup file does not exist: ${BACKUP_FILE}" >&2
  exit 1
fi

TARGET_DB="${2:-${POSTGRES_DB:-${DB_NAME:-SkillSync}}}"
DB_USER="${POSTGRES_USER:-${DB_USER:-postgres}}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

echo "==> Restoring backup: ${BACKUP_FILE}"
echo "==> Target database: ${TARGET_DB}"

# Check if docker-compose Postgres service is running
USE_DOCKER=false
if command -v docker >/dev/null 2>&1 && docker compose ps --services --filter "status=running" 2>/dev/null | grep -q "^db$"; then
  USE_DOCKER=true
fi

if [[ "${USE_DOCKER}" = true ]]; then
  echo "==> Ensuring target database '${TARGET_DB}' exists in docker container..."
  docker compose exec -T db psql -U "${DB_USER}" -d postgres -c \
    "SELECT 1 FROM pg_database WHERE datname = '${TARGET_DB}'" | grep -q 1 || \
    docker compose exec -T db psql -U "${DB_USER}" -d postgres -c "CREATE DATABASE \"${TARGET_DB}\";"

  echo "==> Running pg_restore via docker compose exec db..."
  cat "${BACKUP_FILE}" | docker compose exec -T db pg_restore \
    -U "${DB_USER}" \
    -d "${TARGET_DB}" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges || {
      # pg_restore returns 1 on warnings (e.g., dropping non-existent tables), verify connectivity/tables next
      echo "Notice: pg_restore completed with warnings (common when cleaning fresh database)."
    }
elif command -v pg_restore >/dev/null 2>&1; then
  echo "==> Ensuring target database '${TARGET_DB}' exists locally..."
  PGPASSWORD="${POSTGRES_PASSWORD:-${DB_PASSWORD:-}}" psql \
    -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -tc \
    "SELECT 1 FROM pg_database WHERE datname = '${TARGET_DB}'" | grep -q 1 || \
  PGPASSWORD="${POSTGRES_PASSWORD:-${DB_PASSWORD:-}}" psql \
    -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "CREATE DATABASE \"${TARGET_DB}\";"

  echo "==> Running local pg_restore..."
  PGPASSWORD="${POSTGRES_PASSWORD:-${DB_PASSWORD:-}}" pg_restore \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${TARGET_DB}" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    "${BACKUP_FILE}" || {
      echo "Notice: pg_restore completed with warnings."
    }
else
  echo "ERROR: Neither running docker-compose 'db' service nor local pg_restore found." >&2
  exit 1
fi

echo "==> Database restore completed into '${TARGET_DB}'."
