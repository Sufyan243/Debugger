"""email verification columns

Revision ID: 010
Revises: 009
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('verification_token', sa.String(128), nullable=True))
    op.add_column('users', sa.Column('verification_token_expires_at', sa.DateTime(timezone=True), nullable=True))
    # Legacy email accounts pre-date verification — mark them verified so they
    # are not locked out after deployment. New accounts start unverified.
    op.execute("UPDATE users SET email_verified = true WHERE provider = 'email'")


def downgrade():
    op.drop_column('users', 'verification_token_expires_at')
    op.drop_column('users', 'verification_token')
    op.drop_column('users', 'email_verified')
