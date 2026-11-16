# NOOP Home Lab — Database Migrations Guide

NOOP Home Lab manages PostgreSQL schema evolution via [Alembic](https://alembic.sqlalchemy.org/). Migrations are version-controlled and applied deterministically.

---

## 1. Structure

```
homelab/
|-- migrations/
|   |-- alembic.ini             # Alembic configuration
|   |-- env.py                  # Migration runner environment
|   |-- script.py.mako          # Revision template
|   |-- versions/
|       |-- 001_initial_schema.py # Initial baseline migration
```

---

## 2. Applying Migrations

### Running Migrations in Docker

To apply all pending migrations against the live database:

```bash
docker compose exec api alembic -c /app/../migrations/alembic.ini upgrade head
```

Or from within the `homelab/` directory with Python installed:

```bash
alembic -c migrations/alembic.ini upgrade head
```

---

## 3. Creating New Migrations

To generate a new auto-detected migration after updating models in `homelab/api/app/models/`:

```bash
docker compose exec api alembic -c /app/../migrations/alembic.ini revision --autogenerate -m "describe_change"
```

Inspect the generated migration file under `homelab/migrations/versions/` before applying.

---

## 4. Rollback Instructions

To roll back the last migration:

```bash
docker compose exec api alembic -c /app/../migrations/alembic.ini downgrade -1
```

To roll back all migrations to base:

```bash
docker compose exec api alembic -c /app/../migrations/alembic.ini downgrade base
```

---

## 5. Safe Migration Rules

1. **Additive Changes First**: Add new nullable columns or tables before dropping obsolete structures.
2. **Never Mutate Historical Migrations**: Once committed, a migration revision is immutable. Create a new revision to apply fixes.
3. **Always Test Rollback**: Verify that `downgrade()` reverses `upgrade()` cleanly.
