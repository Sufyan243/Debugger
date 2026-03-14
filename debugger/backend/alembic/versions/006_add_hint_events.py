"""add_hint_events

Revision ID: 006
Revises: 005
Create Date: 2024-01-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'hint_events',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('submission_id', sa.UUID(), sa.ForeignKey('code_submissions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('hint_text', sa.Text(), nullable=False),
        sa.Column('affected_line', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_hint_events_session_id', 'hint_events', ['session_id'])


def downgrade() -> None:
    op.drop_index('ix_hint_events_session_id', table_name='hint_events')
    op.drop_table('hint_events')
