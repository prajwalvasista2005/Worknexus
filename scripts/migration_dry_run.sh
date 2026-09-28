#!/usr/bin/env bash
# ==============================================================================
# scripts/migration_dry_run.sh
# Performs an automated dry-run of database migrations against an isolated
# throwaway PostgreSQL database (worknexus_dryrun).
# Verifies data integrity, schema consistency, and reversibility.
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

# Prioritize virtual environment if present
if [[ -d "${REPO_ROOT}/backend/venv/Scripts" ]]; then
  export PATH="${REPO_ROOT}/backend/venv/Scripts:${PATH}"
elif [[ -d "${REPO_ROOT}/backend/venv/bin" ]]; then
  export PATH="${REPO_ROOT}/backend/venv/bin:${PATH}"
elif [[ -d "${REPO_ROOT}/venv/Scripts" ]]; then
  export PATH="${REPO_ROOT}/venv/Scripts:${PATH}"
elif [[ -d "${REPO_ROOT}/venv/bin" ]]; then
  export PATH="${REPO_ROOT}/venv/bin:${PATH}"
fi

PYTHON_BIN="python3"
if command -v python >/dev/null 2>&1 && python -c "import sys" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

DB_USER="${POSTGRES_USER:-${DB_USER:-postgres}}"
DB_PASS="${POSTGRES_PASSWORD:-${DB_PASSWORD:-}}"
SOURCE_DB="${POSTGRES_DB:-${DB_NAME:-SkillSync}}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DRYRUN_DB="worknexus_dryrun"

# Check execution environment (docker vs host)
USE_DOCKER=false
if command -v docker >/dev/null 2>&1 && docker compose ps --services --filter "status=running" 2>/dev/null | grep -q "^db$"; then
  USE_DOCKER=true
fi

# Helper to run psql queries against dry-run database
run_sql() {
  local db="$1"
  local query="$2"
  if [[ "${USE_DOCKER}" = true ]]; then
    docker compose exec -T db psql -U "${DB_USER}" -d "${db}" -t -A -c "${query}"
  else
    PGPASSWORD="${DB_PASS}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${db}" -t -A -c "${query}"
  fi
}

# Helper to run psql with tabular output
run_sql_formatted() {
  local db="$1"
  local query="$2"
  if [[ "${USE_DOCKER}" = true ]]; then
    docker compose exec -T db psql -U "${DB_USER}" -d "${db}" -c "${query}"
  else
    PGPASSWORD="${DB_PASS}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${db}" -c "${query}"
  fi
}

echo "========================================================================"
echo "          WorkNexus Migration Dry-Run & Safety Verification             "
echo "========================================================================"
echo "Source Database:   ${SOURCE_DB}"
echo "Throwaway Database: ${DRYRUN_DB}"
echo "Database Host:     ${DB_HOST}:${DB_PORT} (Docker: ${USE_DOCKER})"
echo "========================================================================"

# Step a: Take fresh backup of source database
TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
BACKUP_FILE="${REPO_ROOT}/backups/dryrun_pre_${TIMESTAMP}.dump"
echo "==> Step (a): Creating fresh backup of '${SOURCE_DB}'..."
bash "${SCRIPT_DIR}/db_backup.sh" "${BACKUP_FILE}"

# Step b: Reset and restore into throwaway database
echo "==> Step (b): Setting up throwaway database '${DRYRUN_DB}'..."
if [[ "${USE_DOCKER}" = true ]]; then
  docker compose exec -T db psql -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS \"${DRYRUN_DB}\";"
  docker compose exec -T db psql -U "${DB_USER}" -d postgres -c "CREATE DATABASE \"${DRYRUN_DB}\";"
else
  PGPASSWORD="${DB_PASS}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS \"${DRYRUN_DB}\";"
  PGPASSWORD="${DB_PASS}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "CREATE DATABASE \"${DRYRUN_DB}\";"
fi

echo "==> Restoring source dump into '${DRYRUN_DB}'..."
bash "${SCRIPT_DIR}/db_restore.sh" "${BACKUP_FILE}" "${DRYRUN_DB}"

# Collect row counts before migration
echo "==> Capturing table statistics before migration..."
TABLES_QUERY="SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name;"
PRE_TABLES=$(run_sql "${DRYRUN_DB}" "${TABLES_QUERY}" || true)

declare -A PRE_COUNTS
for tbl in ${PRE_TABLES}; do
  cnt=$(run_sql "${DRYRUN_DB}" "SELECT count(*) FROM \"${tbl}\";" 2>/dev/null || echo "0")
  PRE_COUNTS["${tbl}"]="${cnt}"
done

# Step c: Run alembic upgrade head against dryrun database
echo "==> Step (c): Executing 'alembic upgrade head' against '${DRYRUN_DB}'..."
ALEMBIC_CONFIG="${REPO_ROOT}/backend/alembic.ini"
ENCODED_PASS=$(${PYTHON_BIN} -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "${DB_PASS}" 2>/dev/null || echo "${DB_PASS}")
DRYRUN_URL="postgresql://${DB_USER}:${ENCODED_PASS}@${DB_HOST}:${DB_PORT}/${DRYRUN_DB}"

# Execute alembic in backend dir
(
  cd "${REPO_ROOT}/backend"
  DATABASE_URL="${DRYRUN_URL}" PYTHONPATH="${REPO_ROOT}/backend:${REPO_ROOT}" ${PYTHON_BIN} -m alembic -c "${ALEMBIC_CONFIG}" upgrade head
)

echo "==> Migration upgrade successful."

# Step d: Run data integrity and normalization checks
echo "==> Step (d): Running post-migration data integrity verification..."
FAILED_CHECKS=0

echo ""
echo "--- 1. Table Row Counts (Before vs After) ---"
POST_TABLES=$(run_sql "${DRYRUN_DB}" "${TABLES_QUERY}")
for tbl in ${POST_TABLES}; do
  cnt_before="${PRE_COUNTS[${tbl}]:-N/A (new table)}"
  cnt_after=$(run_sql "${DRYRUN_DB}" "SELECT count(*) FROM \"${tbl}\";")
  printf "%-30s | Before: %-15s | After: %-15s\n" "${tbl}" "${cnt_before}" "${cnt_after}"
done

echo ""
echo "--- 2. Duplicate Lowercased Emails Check ---"
DUP_EMAILS=$(run_sql "${DRYRUN_DB}" "SELECT lower(email), count(*) FROM users GROUP BY lower(email) HAVING count(*) > 1;" || true)
if [[ -n "${DUP_EMAILS}" ]]; then
  echo "FAIL: Detected users with duplicate lowercased emails:" >&2
  run_sql_formatted "${DRYRUN_DB}" "SELECT lower(email), count(*), array_agg(id) as ids FROM users GROUP BY lower(email) HAVING count(*) > 1;" >&2
  FAILED_CHECKS=$((FAILED_CHECKS + 1))
else
  echo "PASS: No duplicate lowercased emails found."
fi

echo ""
echo "--- 3. Allowed Role Enum Normalization Check ---"
INVALID_ROLES=$(run_sql "${DRYRUN_DB}" "SELECT id, email, role FROM users WHERE lower(role) NOT IN ('student', 'employer', 'institute', 'trainer', 'admin');" || true)
if [[ -n "${INVALID_ROLES}" ]]; then
  echo "FAIL: Detected users with invalid or unnormalized roles:" >&2
  run_sql_formatted "${DRYRUN_DB}" "SELECT id, email, role FROM users WHERE lower(role) NOT IN ('student', 'employer', 'institute', 'trainer', 'admin');" >&2
  FAILED_CHECKS=$((FAILED_CHECKS + 1))
else
  echo "PASS: All user roles normalized to allowed enum values."
fi

echo ""
echo "--- 4. Employers NULL user_id Check ---"
NULL_USER_EMPLOYERS=$(run_sql "${DRYRUN_DB}" "SELECT id, company_name FROM employers WHERE user_id IS NULL;" || true)
if [[ -n "${NULL_USER_EMPLOYERS}" ]]; then
  echo "FAIL: Detected employers with NULL user_id:" >&2
  run_sql_formatted "${DRYRUN_DB}" "SELECT id, company_name FROM employers WHERE user_id IS NULL;" >&2
  FAILED_CHECKS=$((FAILED_CHECKS + 1))
else
  echo "PASS: All employer records have non-NULL user_id."
fi

echo ""
echo "--- 5. Employer user_id Role & Mapping Verification ---"
MISMATCHED_EMPLOYERS=$(run_sql "${DRYRUN_DB}" "SELECT e.id, e.company_name, u.id, u.role, u.email FROM employers e JOIN users u ON e.user_id = u.id WHERE lower(u.role) != 'employer';" || true)
if [[ -n "${MISMATCHED_EMPLOYERS}" ]]; then
  echo "FAIL: Detected employers mapped to users with incorrect role:" >&2
  run_sql_formatted "${DRYRUN_DB}" "SELECT e.id, e.company_name, u.id, u.role, u.email FROM employers e JOIN users u ON e.user_id = u.id WHERE lower(u.role) != 'employer';" >&2
  FAILED_CHECKS=$((FAILED_CHECKS + 1))
else
  echo "PASS: All employers map to users with 'employer' role."
fi

echo ""
echo "--- 6. Job Skills Integer Skill FK Mapping Check ---"
UNMAPPED_JOB_SKILLS=$(run_sql "${DRYRUN_DB}" "SELECT js.id, js.job_id, js.skill_id FROM job_skills js LEFT JOIN skills s ON js.skill_id = s.id WHERE s.id IS NULL;" || true)
if [[ -n "${UNMAPPED_JOB_SKILLS}" ]]; then
  echo "FAIL: Detected job_skills rows that fail to map to a valid integer skill ID:" >&2
  run_sql_formatted "${DRYRUN_DB}" "SELECT js.id, js.job_id, js.skill_id FROM job_skills js LEFT JOIN skills s ON js.skill_id = s.id WHERE s.id IS NULL;" >&2
  FAILED_CHECKS=$((FAILED_CHECKS + 1))
else
  echo "PASS: All job_skills reference valid integer skill IDs."
fi

echo ""
echo "--- 7. Orphaned Employer Feedback Signals Check ---"
FEEDBACK_TABLE_EXISTS=$(run_sql "${DRYRUN_DB}" "SELECT 1 FROM information_schema.tables WHERE table_name = 'employer_feedback_signals';" || true)
if [[ "${FEEDBACK_TABLE_EXISTS}" = "1" ]]; then
  ORPHAN_SIGNALS=$(run_sql "${DRYRUN_DB}" "SELECT s.id, s.skill_id FROM employer_feedback_signals s LEFT JOIN skills sk ON CAST(s.skill_id AS text) = CAST(sk.id AS text) WHERE sk.id IS NULL;" || true)
  if [[ -n "${ORPHAN_SIGNALS}" ]]; then
    echo "FAIL: Detected orphaned employer_feedback_signals:" >&2
    run_sql_formatted "${DRYRUN_DB}" "SELECT s.id, s.skill_id FROM employer_feedback_signals s LEFT JOIN skills sk ON CAST(s.skill_id AS text) = CAST(sk.id AS text) WHERE sk.id IS NULL;" >&2
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
  else
    echo "PASS: No orphaned employer_feedback_signals detected."
  fi
else
  echo "INFO: Table 'employer_feedback_signals' does not exist yet."
fi

echo ""
echo "--- 8. Refresh Tokens Count ---"
REFRESH_TABLE_EXISTS=$(run_sql "${DRYRUN_DB}" "SELECT 1 FROM information_schema.tables WHERE table_name = 'refresh_tokens';" || true)
if [[ "${REFRESH_TABLE_EXISTS}" = "1" ]]; then
  REFRESH_COUNT=$(run_sql "${DRYRUN_DB}" "SELECT count(*) FROM refresh_tokens;")
  echo "INFO: Total refresh tokens in database: ${REFRESH_COUNT}"
else
  echo "INFO: Table 'refresh_tokens' does not exist yet."
fi

# Step e: Verify reversibility with downgrade -1 and re-upgrade
echo ""
echo "==> Step (e): Verifying reversibility (downgrade -1 followed by re-upgrade)..."
(
  cd "${REPO_ROOT}/backend"
  DATABASE_URL="${DRYRUN_URL}" PYTHONPATH="${REPO_ROOT}/backend:${REPO_ROOT}" ${PYTHON_BIN} -m alembic -c "${ALEMBIC_CONFIG}" downgrade -1
  DATABASE_URL="${DRYRUN_URL}" PYTHONPATH="${REPO_ROOT}/backend:${REPO_ROOT}" ${PYTHON_BIN} -m alembic -c "${ALEMBIC_CONFIG}" upgrade head
)
echo "==> Reversibility check passed."

# Step f: Cleanup throwaway database and exit
echo ""
if [[ ${FAILED_CHECKS} -gt 0 ]]; then
  echo "========================================================================" >&2
  echo "ERROR: Dry-run migration verification FAILED with ${FAILED_CHECKS} integrity issue(s)." >&2
  echo "Preserving throwaway database '${DRYRUN_DB}' for inspection." >&2
  echo "========================================================================" >&2
  exit 1
else
  echo "==> Step (f): Cleaning up throwaway database '${DRYRUN_DB}'..."
  if [[ "${USE_DOCKER}" = true ]]; then
    docker compose exec -T db psql -U "${DB_USER}" -d postgres -c "DROP DATABASE \"${DRYRUN_DB}\";"
  else
    PGPASSWORD="${DB_PASS}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "DROP DATABASE \"${DRYRUN_DB}\";"
  fi
  echo "========================================================================"
  echo "SUCCESS: Migration dry-run completed with zero integrity violations!"
  echo "========================================================================"
  exit 0
fi
