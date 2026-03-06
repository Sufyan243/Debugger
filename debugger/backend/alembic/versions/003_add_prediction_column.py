"""add_prediction_column

Revision ID: 003
Revises: 002
Create Date: 2024-01-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('code_submissions', sa.Column('prediction', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('code_submissions', 'prediction')
