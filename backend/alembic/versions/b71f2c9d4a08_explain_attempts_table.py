"""explain attempts table

Revision ID: b71f2c9d4a08
Revises: e76d8fa1205c
Create Date: 2026-11-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b71f2c9d4a08'
down_revision: Union[str, Sequence[str], None] = 'e76d8fa1205c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('explain_attempt',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('exam_id', sa.Integer(), nullable=True),
    sa.Column('question_id', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('accuracy', sa.Integer(), nullable=False, server_default='0'),
    sa.Column('completeness', sa.Integer(), nullable=False, server_default='0'),
    sa.Column('own_words', sa.Integer(), nullable=False, server_default='0'),
    sa.Column('score_10', sa.Integer(), nullable=False, server_default='0'),
    sa.Column('xp', sa.Integer(), nullable=False, server_default='0'),
    sa.Column('feedback', sa.Text(), nullable=False, server_default=''),
    sa.Column('graded', sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['exam_id'], ['exam.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['question_id'], ['question.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_explain_attempt_exam_id'), 'explain_attempt', ['exam_id'], unique=False)
    op.create_index(op.f('ix_explain_attempt_question_id'), 'explain_attempt', ['question_id'], unique=False)
    op.create_index(op.f('ix_explain_attempt_user_id'), 'explain_attempt', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_explain_attempt_user_id'), table_name='explain_attempt')
    op.drop_index(op.f('ix_explain_attempt_question_id'), table_name='explain_attempt')
    op.drop_index(op.f('ix_explain_attempt_exam_id'), table_name='explain_attempt')
    op.drop_table('explain_attempt')
