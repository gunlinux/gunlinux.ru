"""Replace PostgreSQL-specific types with generic SQLAlchemy types

Revision ID: f00000000002
Revises: f00000000001
Create Date: 2025-09-08 23:35:00.000000

"""

# revision identifiers, used by Alembic.
revision = "f00000000002"
down_revision = "f00000000001"
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade the database schema to use generic types instead of PostgreSQL-specific types."""
    # This migration fixes PostgreSQL-specific type references
    # Since we're using generic SQLAlchemy types, no changes are needed
    # This is a placeholder to ensure migration chain integrity
    pass


def downgrade():
    """Downgrade the database schema."""
    # No changes needed for downgrade
    pass
