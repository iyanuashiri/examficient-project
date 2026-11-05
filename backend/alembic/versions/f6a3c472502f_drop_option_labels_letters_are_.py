"""drop option labels letters are presentation

Revision ID: f6a3c472502f
Revises: e0c24adfda58
Create Date: 2026-11-04 14:31:58.202572

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a3c472502f'
down_revision: Union[str, Sequence[str], None] = 'e0c24adfda58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("option") as batch_op:
        batch_op.drop_constraint("ck_option_label", type_="check")
        batch_op.drop_constraint("uq_option_question_label", type_="unique")
        batch_op.drop_column("label")
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("option") as batch_op:
        batch_op.add_column(sa.Column("label", sa.VARCHAR(length=4), nullable=False, server_default=""))
        batch_op.create_unique_constraint("uq_option_question_label", ["question_id", "label"])
    # ### end Alembic commands ###
