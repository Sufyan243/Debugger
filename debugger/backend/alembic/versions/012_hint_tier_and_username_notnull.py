"""hint_tier_and_username_notnull

Revision ID: 012
Revises: 011
Create Date: 2025-01-12 00:00:00.000000

Changes:
  1. Add nullable `tier` column to `hint_events` — required by hint/solution
     progression gates that query HintEvent.tier explicitly.
  2. Drop `uq_users_username` unique constraint — username collisions are
     expected for OAuth users sharing a display name; uniqueness was removed
     from the ORM model in the OAuth username-collision fix.
"""
from alembic import op
import sqlalchemy as sa

revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add nullable tier column to hint_events.
    #    Existing rows get NULL, which is safe — the progression gate only
    #    queries rows where tier IS NOT NULL (explicit tier history).
    op.add_column('hint_events', sa.Column('tier', sa.Integer(), nullable=True))

    # 2. Drop the username uniqueness constraint introduced in migration 008.
    #    Use batch mode for SQLite compatibility; on Postgres the constraint
    #    name is 'uq_users_username' as created in 008.
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_constraint('uq_users_username', type_='unique')


def downgrade() -> None:
    # Re-add the username unique constraint.
    # WARNING: this will fail if duplicate usernames already exist in the DB.
    # Callers must deduplicate rows before running downgrade.
    with op.batch_alter_table('users') as batch_op:
        batch_op.create_unique_constraint('uq_users_username', ['username'])

    # Drop the tier column; existing tier data is lost on downgrade.
    op.drop_column('hint_events', 'tier')
