# WorkNexus Database Migration & Operational Safety Protocol

This document defines the strict, mandatory operational runbook required before executing database migrations in any staging, pre-production, or production environment containing real or non-disposable data.

---

## 1. Zero-Assumption Principle

Under no circumstances may migrations be executed directly against a live production database without executing the complete safety checklist below:
1. **Never guess**: Backfills that encounter ambiguous mapping (e.g. multiple candidate accounts or conflicting names) are programmed to fail loudly and abort the migration.
2. **Never skip backups**: A custom-format binary dump (`pg_dump -Fc`) must be verified on disk before any DDL or DML transaction begins.
3. **Always dry-run**: Every schema and data migration must pass automated verification on an isolated clone of production data before touching live storage.

---

## 2. Pre-Migration Runbook

### Step 1: Mandatory Full Backup
Create a timestamped binary backup using `scripts/db_backup.sh`. The script uses `pg_dump -Fc` and refuses to overwrite existing files.

```bash
# If using Docker Compose (executes against the running db service):
./scripts/db_backup.sh

# Or specify a custom output path:
./scripts/db_backup.sh backups/production_pre_migration_$(date +%Y%m%d_%H%M%S).dump
```

Verify that the backup file exists, is non-empty, and has a size consistent with expectations:
```bash
ls -lh backups/
```

### Step 2: Automated Dry-Run on Throwaway Database
Execute `scripts/migration_dry_run.sh`. This script performs the following fully automated sequence:
1. Generates an instantaneous backup of the source database.
2. Creates an isolated throwaway database (`worknexus_dryrun`).
3. Restores the backup into the throwaway database.
4. Gathers baseline statistics (table row counts).
5. Runs `alembic upgrade head` against `worknexus_dryrun`.
6. Executes the 8 data-integrity audit checks:
   - Table row count preservation (before vs. after).
   - Detection of duplicate lowercased emails (`lower(email)`).
   - Verification that all user roles match allowed enum values (`student`, `employer`, `institute`, `trainer`, `admin`).
   - Detection of employer records with NULL `user_id`.
   - Verification that all linked employers map to users with the `employer` role.
   - Verification that all `job_skills` reference valid integer `skill_id` foreign keys.
   - Verification of zero orphaned feedback signals.
   - Verification of active refresh tokens.
7. Verifies reversibility by executing `alembic downgrade -1` followed by `alembic upgrade head`.
8. Tears down `worknexus_dryrun` if and only if all checks pass.

```bash
./scripts/migration_dry_run.sh
```

If the dry-run fails with an exit code of `1`:
- **STOP IMMEDIATELY**.
- Inspect the output report to identify the offending rows or integrity violations.
- Do NOT proceed to live migration until the offending data is reconciled.

---

## 3. Maintenance Window & Execution

### Step 3: Traffic Draining
1. Notify stakeholders of scheduled maintenance.
2. Direct upstream load balancers / reverse proxies to maintenance mode or suspend ingress traffic to the FastAPI backend.
3. Terminate running background tasks.

### Step 4: Execute Live Migration
Navigate to the `backend` directory and apply the migration transaction:

```bash
cd backend
alembic upgrade head
```

Alembic wraps each migration step within a transaction (`with context.begin_transaction():`). If any migration step encounters an error, the transaction is automatically rolled back.

### Step 5: Post-Migration Smoke Test
1. Check Alembic current revision:
   ```bash
   alembic current
   ```
2. Verify application connectivity and health endpoints:
   ```bash
   curl -f http://localhost:8000/health/ready
   ```
3. Run critical authentication and workflow smoke tests.
4. Re-enable traffic at the load balancer.

---

## 4. Rollback and Disaster Recovery Plan

If unexpected failures, runtime errors, or severe performance degradation occur after live migration, execute the rollback procedure immediately:

### Option A: Clean Alembic Downgrade (Schema-Only or Reversible Migrations)
If the migration cleanly supports downgrade:
```bash
cd backend
alembic downgrade -1
```

### Option B: Full Restoration from Pre-Migration Backup (Data Corruption or Irreversible Changes)
If data was modified destructively or an abort corrupted intermediate state:
1. Immediately stop the backend service:
   ```bash
   docker compose stop backend
   ```
2. Restore the database using `scripts/db_restore.sh`:
   ```bash
   ./scripts/db_restore.sh backups/<PRE_MIGRATION_BACKUP_FILE>.dump SkillSync
   ```
3. Restart backend service and verify operational status:
   ```bash
   docker compose start backend
   curl -f http://localhost:8000/health/ready
   ```
