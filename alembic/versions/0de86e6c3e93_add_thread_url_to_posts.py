"""add_thread_url_to_posts

Revision ID: 0de86e6c3e93
Revises: 43f3c40864f6
Create Date: 2025-09-08 15:14:11.136311

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0de86e6c3e93'
down_revision = '43f3c40864f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add thread_url column to posts table
    op.add_column('posts', sa.Column('thread_url', sa.String(500), nullable=True))
    # Add index for better query performance
    op.create_index('ix_posts_thread_url', 'posts', ['thread_url'])


def downgrade() -> None:
    # Remove thread_url column and index
    op.drop_index('ix_posts_thread_url', table_name='posts')
    op.drop_column('posts', 'thread_url')
