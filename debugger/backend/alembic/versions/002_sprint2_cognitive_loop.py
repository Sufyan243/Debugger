"""sprint2_cognitive_loop

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('hint_sequences',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('concept_category', sa.String(length=200), nullable=False),
    sa.Column('tier', sa.Integer(), nullable=False),
    sa.Column('tier_name', sa.String(length=50), nullable=False),
    sa.Column('hint_text', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('concept_category', 'tier', name='uq_concept_tier')
    )
    
    op.create_table('reflection_responses',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('submission_id', sa.UUID(), nullable=False),
    sa.Column('response_text', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('hint_unlocked', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['submission_id'], ['code_submissions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('solution_requests',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('submission_id', sa.UUID(), nullable=False),
    sa.Column('request_count', sa.Integer(), nullable=True),
    sa.Column('solution_revealed', sa.Boolean(), nullable=True),
    sa.Column('last_requested_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['submission_id'], ['code_submissions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('submission_id')
    )
    
    op.add_column('error_records', sa.Column('failed_attempts', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    op.drop_column('error_records', 'failed_attempts')
    op.drop_table('solution_requests')
    op.drop_table('reflection_responses')
    op.drop_table('hint_sequences')
