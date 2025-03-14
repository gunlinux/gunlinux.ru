"""passing users

Revision ID: 17233218b5e1
Revises: 6d3cbb911de3
Create Date: 2024-04-29 21:28:03.342702

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "17233218b5e1"
down_revision = "6d3cbb911de3"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.INTEGER(), nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.INTEGER(), nullable=True)

    # ### end Alembic commands ###
