"""Fix PostgreSQL-specific migration for cross-database compatibility

Revision ID: f00000000001
Revises: b0e3595603e9
Create Date: 2025-09-08 23:30:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f00000000001"
down_revision = "b0e3595603e9"
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade the database schema to fix issues and improve consistency."""
    # Fix issues with nullable columns that should not be nullable
    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.alter_column(
            "title", existing_type=sa.VARCHAR(length=255), nullable=False
        )
        batch_op.alter_column(
            "alias", existing_type=sa.VARCHAR(length=255), nullable=False
        )

    with op.batch_alter_table("icons", schema=None) as batch_op:
        batch_op.alter_column(
            "title", existing_type=sa.VARCHAR(length=255), nullable=False
        )
        batch_op.alter_column(
            "url", existing_type=sa.VARCHAR(length=255), nullable=False
        )
        # Allow content to be nullable for icons
        batch_op.alter_column("content", existing_type=sa.TEXT(), nullable=True)

    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.alter_column(
            "pagetitle", existing_type=sa.VARCHAR(length=255), nullable=False
        )
        batch_op.alter_column(
            "alias", existing_type=sa.VARCHAR(length=255), nullable=False
        )
        # Allow content to be nullable for drafts
        batch_op.alter_column("content", existing_type=sa.TEXT(), nullable=True)
        batch_op.alter_column("createdon", existing_type=sa.DATETIME(), nullable=False)

    with op.batch_alter_table("tags", schema=None) as batch_op:
        batch_op.alter_column(
            "title", existing_type=sa.VARCHAR(length=255), nullable=False
        )
        batch_op.alter_column(
            "alias", existing_type=sa.VARCHAR(length=255), nullable=False
        )

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "name", existing_type=sa.VARCHAR(length=50), nullable=False
        )
        # Password should be nullable to allow for external auth
        batch_op.alter_column(
            "password", existing_type=sa.VARCHAR(length=255), nullable=True
        )
        # Fix authenticated column type
        batch_op.alter_column(
            "authenticated", existing_type=sa.Integer(), nullable=True
        )


def downgrade():
    """Downgrade the database schema to the previous state."""
    # Revert changes to nullable columns
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "authenticated", existing_type=sa.Integer(), nullable=True
        )
        batch_op.alter_column(
            "password", existing_type=sa.VARCHAR(length=255), nullable=True
        )
        batch_op.alter_column(
            "name", existing_type=sa.VARCHAR(length=50), nullable=True
        )

    with op.batch_alter_table("tags", schema=None) as batch_op:
        batch_op.alter_column(
            "alias", existing_type=sa.VARCHAR(length=255), nullable=True
        )
        batch_op.alter_column(
            "title", existing_type=sa.VARCHAR(length=255), nullable=True
        )

    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.alter_column("createdon", existing_type=sa.DATETIME(), nullable=True)
        batch_op.alter_column("content", existing_type=sa.TEXT(), nullable=True)
        batch_op.alter_column(
            "alias", existing_type=sa.VARCHAR(length=255), nullable=True
        )
        batch_op.alter_column(
            "pagetitle", existing_type=sa.VARCHAR(length=255), nullable=True
        )

    with op.batch_alter_table("icons", schema=None) as batch_op:
        batch_op.alter_column("content", existing_type=sa.TEXT(), nullable=True)
        batch_op.alter_column(
            "url", existing_type=sa.VARCHAR(length=255), nullable=True
        )
        batch_op.alter_column(
            "title", existing_type=sa.VARCHAR(length=255), nullable=True
        )

    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.alter_column(
            "alias", existing_type=sa.VARCHAR(length=255), nullable=True
        )
        batch_op.alter_column(
            "title", existing_type=sa.VARCHAR(length=255), nullable=True
        )
