"""user.auth

Revision ID: ee21045f7c54
Revises: 812581da765a
Create Date: 2024-04-29 21:45:40.260994

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "ee21045f7c54"
down_revision = "812581da765a"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("authenticated", sa.Boolean(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column("password", existing_type=sa.VARCHAR(), nullable=True)
        batch_op.drop_column("authenticated")

    # ### end Alembic commands ###
