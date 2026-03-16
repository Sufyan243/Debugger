"""oauth_and_anon_sessions

Revision ID: 009
Revises: 008
Create Date: 2024-01-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extend users table
    op.add_column('users', sa.Column('email', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('provider', sa.String(20), nullable=False, server_default='email'))
    op.add_column('users', sa.Column('provider_id', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.String(500), nullable=True))
    op.alter_column('users', 'username', nullable=True)
    op.alter_column('users', 'hashed_password', nullable=True)
    op.create_unique_constraint('uq_users_email', 'users', ['email'])
    op.create_unique_constraint('uq_users_provider_id', 'users', ['provider', 'provider_id'])

    # Anon sessions table
    op.create_table(
        'anon_sessions',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('merged_into', sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('anon_sessions')
    op.drop_constraint('uq_users_provider_id', 'users', type_='unique')
    op.drop_constraint('uq_users_email', 'users', type_='unique')
    op.alter_column('users', 'hashed_password', nullable=False)
    op.alter_column('users', 'username', nullable=False)
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'provider_id')
    op.drop_column('users', 'provider')
    op.drop_column('users', 'email')
