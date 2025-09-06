"""add missing posts columns

Revision ID: add_missing_posts_columns
Revises: merge_branches_001
Create Date: 2025-09-06 20:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_missing_posts_columns"
down_revision = "merge_branches_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing columns to posts table
    op.execute("ALTER TABLE posts ADD COLUMN IF NOT EXISTS post_id VARCHAR(255)")
    op.execute("ALTER TABLE posts ADD COLUMN IF NOT EXISTS url VARCHAR(500)")
    
    # Create indexes for the new columns
    op.execute("CREATE INDEX IF NOT EXISTS ix_posts_post_id ON posts (post_id)")
    
    # Update post_id with a default value for existing records (using id as fallback)
    op.execute("UPDATE posts SET post_id = CONCAT('post_', id) WHERE post_id IS NULL OR post_id = ''")


def downgrade() -> None:
    # Remove the added columns
    op.execute("DROP INDEX IF EXISTS ix_posts_post_id")
    op.execute("ALTER TABLE posts DROP COLUMN IF EXISTS url")
    op.execute("ALTER TABLE posts DROP COLUMN IF EXISTS post_id")