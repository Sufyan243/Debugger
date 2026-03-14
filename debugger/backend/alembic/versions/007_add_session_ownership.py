"""add_session_ownership

Revision ID: 007
Revises: 006
Create Date: 2024-01-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'session_ownership',
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('owner_token', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('session_id'),
        sa.UniqueConstraint('owner_token', name='uq_session_ownership_token'),
    )


def downgrade() -> None:
    op.drop_table('session_ownership')
