"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create issues table
    op.create_table(
        'issues',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repo', sa.Text(), nullable=False),
        sa.Column('issue_number', sa.Integer(), nullable=False),
        sa.Column('checklist', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_issues_repo_issue_number', 'issues', ['repo', 'issue_number'], unique=False)
    op.create_index('ix_issues_id', 'issues', ['id'], unique=False)
    
    # Create pull_requests table
    op.create_table(
        'pull_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repo', sa.Text(), nullable=False),
        sa.Column('pr_number', sa.Integer(), nullable=False),
        sa.Column('issue_id', sa.Integer(), nullable=True),
        sa.Column('head_sha', sa.String(length=40), nullable=True),
        sa.Column('test_manifest', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('validation_status', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['issue_id'], ['issues.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pull_requests_repo_pr_number', 'pull_requests', ['repo', 'pr_number'], unique=False)
    op.create_index('ix_pull_requests_id', 'pull_requests', ['id'], unique=False)
    
    # Create test_results table
    op.create_table(
        'test_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pr_id', sa.Integer(), nullable=False),
        sa.Column('test_id', sa.String(length=100), nullable=True),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('log_url', sa.Text(), nullable=True),
        sa.Column('checklist_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['pr_id'], ['pull_requests.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_test_results_id', 'test_results', ['id'], unique=False)
    
    # Create reports table
    op.create_table(
        'reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pr_id', sa.Integer(), nullable=False),
        sa.Column('report_content', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['pr_id'], ['pull_requests.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_reports_id', 'reports', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_reports_id', table_name='reports')
    op.drop_table('reports')
    op.drop_index('ix_test_results_id', table_name='test_results')
    op.drop_table('test_results')
    op.drop_index('ix_pull_requests_repo_pr_number', table_name='pull_requests')
    op.drop_index('ix_pull_requests_id', table_name='pull_requests')
    op.drop_table('pull_requests')
    op.drop_index('ix_issues_repo_issue_number', table_name='issues')
    op.drop_index('ix_issues_id', table_name='issues')
    op.drop_table('issues')

