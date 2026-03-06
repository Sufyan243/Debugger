"""sprint1_initial_schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('concept_categories',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('cognitive_skill', sa.String(length=200), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    
    op.create_table('code_submissions',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('code_text', sa.Text(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=False),
    sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('execution_results',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('submission_id', sa.UUID(), nullable=False),
    sa.Column('stdout', sa.Text(), nullable=True),
    sa.Column('stderr', sa.Text(), nullable=True),
    sa.Column('traceback', sa.Text(), nullable=True),
    sa.Column('execution_time', sa.Float(), nullable=True),
    sa.Column('success_flag', sa.Boolean(), nullable=False),
    sa.Column('timed_out', sa.Boolean(), nullable=True),
    sa.Column('exit_code', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['submission_id'], ['code_submissions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('error_records',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('execution_result_id', sa.UUID(), nullable=False),
    sa.Column('exception_type', sa.String(length=100), nullable=False),
    sa.Column('concept_category', sa.String(length=200), nullable=False),
    sa.Column('cognitive_skill', sa.String(length=200), nullable=True),
    sa.ForeignKeyConstraint(['execution_result_id'], ['execution_results.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('error_records')
    op.drop_table('execution_results')
    op.drop_table('code_submissions')
    op.drop_table('concept_categories')
