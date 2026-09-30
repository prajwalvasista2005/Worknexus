# SkillMesh

SkillMesh (developed by the WorkNexus team) is a unified workforce, skills, and curriculum intelligence platform built with **FastAPI**, **SQLAlchemy**, **Alembic**, **PostgreSQL**, and **React** (Vite).

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

The `.pre-commit-config.yaml` configures two hook collections that run automatically on every `git commit`:

| Hook | Purpose |
|------|---------|
| **gitleaks** | Blocks commits containing secrets, tokens, or private keys |
| **mixed-line-ending** (`--fix=lf`) | Enforces LF line endings on `.sh` and `.py` files (mirrors `.gitattributes`) |
| **trailing-whitespace** | Removes trailing whitespace from `.sh` and `.py` files |
| **end-of-file-fixer** | Ensures `.sh` and `.py` files end with a newline |
| **check-added-large-files** | Rejects files larger than 1 MB accidentally staged |
| **check-yaml** | Validates YAML syntax (workflows, pre-commit config, etc.) |
| **check-json** | Validates JSON syntax (package.json, package-lock.json, etc.) |
| **detect-private-key** | Detects private keys staged for commit |

### Installation Instructions

Install and activate the pre-commit hook in your local Git repository:

```bash
# 1. Install pre-commit (already in backend/requirements.txt)
pip install pre-commit

# 2. Install git hooks into this repository  ← REQUIRED for every fresh clone
pre-commit install

# 3. (Recommended) Run against all tracked files to verify the baseline is clean
pre-commit run --all-files
```

With the hooks installed, Git automatically runs all checks before every commit.
Any violation (leaked secret, Windows CRLF line ending, trailing whitespace, invalid YAML/JSON) **blocks the commit** and prints a clear error message.

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
