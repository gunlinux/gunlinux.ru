"""remove status

Revision ID: 027b40980791
Revises: 4d9ba795cc36
Create Date: 2024-04-29 07:27:43.140553

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "027b40980791"
down_revision = "4d9ba795cc36"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.alter_column(
            "title", existing_type=sa.VARCHAR(length=255), nullable=False
        )

    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.alter_column(
            "pagetitle", existing_type=sa.VARCHAR(length=255), nullable=False
        )
        batch_op.alter_column("content", existing_type=sa.TEXT(), nullable=False)
        batch_op.alter_column("createdon", existing_type=sa.DATETIME(), nullable=False)
        batch_op.alter_column(
            "bg", existing_type=sa.VARCHAR(length=255), nullable=False
        )
        batch_op.drop_column("status")

    with op.batch_alter_table("posts_tags", schema=None) as batch_op:
        batch_op.drop_column("id")

    with op.batch_alter_table("tags", schema=None) as batch_op:
        batch_op.alter_column(
            "title", existing_type=sa.VARCHAR(length=255), nullable=False
        )
        batch_op.alter_column(
            "alias", existing_type=sa.VARCHAR(length=255), nullable=False
        )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("tags", schema=None) as batch_op:
        batch_op.alter_column(
            "alias", existing_type=sa.VARCHAR(length=255), nullable=True
        )
        batch_op.alter_column(
            "title", existing_type=sa.VARCHAR(length=255), nullable=True
        )

    with op.batch_alter_table("posts_tags", schema=None) as batch_op:
        batch_op.add_column(sa.Column("id", sa.INTEGER(), nullable=False))

    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("status", sa.INTEGER(), nullable=True))
        batch_op.alter_column("bg", existing_type=sa.VARCHAR(length=255), nullable=True)
        batch_op.alter_column("createdon", existing_type=sa.DATETIME(), nullable=True)
        batch_op.alter_column("content", existing_type=sa.TEXT(), nullable=True)
        batch_op.alter_column(
            "pagetitle", existing_type=sa.VARCHAR(length=255), nullable=True
        )

    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.alter_column(
            "title", existing_type=sa.VARCHAR(length=255), nullable=True
        )

    # ### end Alembic commands ###
