"""snapshot_dedup_and_reflection_unique

Revision ID: 011
Revises: 010
Create Date: 2024-01-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add date_bucket to session_snapshots and enforce one snapshot per session per day
    op.add_column('session_snapshots', sa.Column('date_bucket', sa.String(10), nullable=False, server_default='1970-01-01'))
    op.create_unique_constraint('uq_snapshot_session_date', 'session_snapshots', ['session_id', 'date_bucket'])

    # Enforce one reflection per submission
    op.create_unique_constraint('uq_reflection_submission', 'reflection_responses', ['submission_id'])


def downgrade() -> None:
    op.drop_constraint('uq_reflection_submission', 'reflection_responses', type_='unique')
    op.drop_constraint('uq_snapshot_session_date', 'session_snapshots', type_='unique')
    op.drop_column('session_snapshots', 'date_bucket')
