# Database Migrations

This directory contains the Alembic migration scripts for the gunlinux.ru blog application.

## Overview

Database migrations allow us to evolve the database schema over time while maintaining data integrity and providing rollback capabilities.

## Directory Structure

- `versions/` - Migration scripts (timestamped)
- `alembic.ini` - Alembic configuration
- `env.py` - Migration environment configuration
- `script.py.mako` - Template for new migration scripts

## Working with Migrations

### Apply Pending Migrations

```bash
flask db upgrade
```

### Create a New Migration

After modifying SQLAlchemy models:

```bash
flask db migrate -m "Description of changes"
```

### Check Current Revision

```bash
flask db current
```

### View Migration History

```bash
flask db history
```

## Best Practices

1. **Review Generated Migrations**: Always review auto-generated migration scripts before committing
2. **Test Migrations**: Test both upgrade and downgrade functions before deploying to production
3. **Version Control**: Commit migration scripts immediately after creation
4. **Descriptive Names**: Give migration scripts descriptive names that explain the changes
5. **Backup Before Production**: Always backup the database before applying migrations in production

## Documentation

For detailed information about migrations, see [docs/migrations.md](../docs/migrations.md).