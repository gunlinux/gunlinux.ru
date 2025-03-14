"""postgres

Revision ID: 81d804b1c18c
Revises: ee21045f7c54
Create Date: 2024-05-01 04:29:32.306896

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "81d804b1c18c"
down_revision = "ee21045f7c54"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.alter_column(
            "createdon",
            existing_type=postgresql.TIMESTAMP(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "publishedon",
            existing_type=postgresql.TIMESTAMP(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=True,
        )

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column("password", existing_type=sa.VARCHAR(), nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column("password", existing_type=sa.VARCHAR(), nullable=True)

    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.alter_column(
            "publishedon",
            existing_type=sa.DateTime(timezone=True),
            type_=postgresql.TIMESTAMP(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "createdon",
            existing_type=sa.DateTime(timezone=True),
            type_=postgresql.TIMESTAMP(),
            existing_nullable=False,
        )

    # ### end Alembic commands ###
