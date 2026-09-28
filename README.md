# WorkNexus

WorkNexus is a unified workforce, skills, and curriculum intelligence platform built with **FastAPI**, **SQLAlchemy**, **Alembic**, **PostgreSQL**, and **React** (Vite).

---

## 1. Quickstart & Local Setup

### Prerequisites
- **Python**: 3.13 (or 3.13+)
- **Node.js**: 22+ & npm
- **Docker & Docker Compose** (for PostgreSQL and containerized services)

### Environment Configuration
Copy the configuration template to `.env`:
```bash
cp .env.example .env
```
Generate and update secret values in `.env`:
- Generate a 32+ character `SECRET_KEY`:
  ```bash
  openssl rand -hex 32
  ```
- Generate a secure database password:
  ```bash
  openssl rand -base64 24
  ```

---

## 2. Pre-Commit Hooks & Secret Detection

To protect credentials from being committed to version control, Gitleaks is configured via `.pre-commit-config.yaml`.

### Installation Instructions
Install and activate the pre-commit hook in your local Git repository:

```bash
# 1. Install pre-commit using pip
pip install pre-commit

# 2. Install git hooks in this repository
pre-commit install

# 3. (Optional) Run against all files to verify baseline
pre-commit run --all-files
```

With the pre-commit hook installed, Git automatically runs Gitleaks before every commit, blocking any commit that contains exposed secrets, tokens, or private keys.

---

## 3. Database Migrations & Operational Safety

All schema migrations are managed exclusively through Alembic and follow strict zero-assumption and dry-run safety protocols.

- **Dry-run verification on isolated database**:
  ```bash
  ./scripts/migration_dry_run.sh
  ```
- **Backup before migration**:
  ```bash
  ./scripts/db_backup.sh
  ```
- **Apply migrations**:
  ```bash
  cd backend
  alembic upgrade head
  ```
- **Restore from backup**:
  ```bash
  ./scripts/db_restore.sh backups/<BACKUP_FILE>.dump SkillSync
  ```

For detailed migration runbooks and disaster recovery steps, refer to [docs/MIGRATIONS.md](docs/MIGRATIONS.md).

---

## 4. Running Tests

Run the full backend test suite with pytest:
```bash
pytest backend/tests -v
```

---

## 5. Running with Docker Compose

Start database, backend, and frontend containers:
```bash
docker compose up -d
```
Verify health status:
```bash
curl http://localhost:8000/health/ready
```
