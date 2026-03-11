"""sprint3_metacognitive

Revision ID: 004
Revises: 003
Create Date: 2024-01-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'metacognitive_metrics',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('accuracy_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_predictions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('correct_predictions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )


def downgrade() -> None:
    op.drop_table('metacognitive_metrics')
