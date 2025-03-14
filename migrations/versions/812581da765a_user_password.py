"""user.password

Revision ID: 812581da765a
Revises: a93c3349ab2f
Create Date: 2024-04-29 21:41:41.108458

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "812581da765a"
down_revision = "a93c3349ab2f"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("password", sa.String(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("password")

    # ### end Alembic commands ###
