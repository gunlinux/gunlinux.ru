"""remove_post_bg

Revision ID: 7c0915b8bf41
Revises: 7bc06f2fee58
Create Date: 2024-04-29 11:00:26.327265

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7c0915b8bf41"
down_revision = "7bc06f2fee58"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.drop_column("bg")

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("bg", sa.VARCHAR(length=255), nullable=True))

    # ### end Alembic commands ###
