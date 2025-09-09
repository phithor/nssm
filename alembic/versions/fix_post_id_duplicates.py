"""fix post_id duplicates and add unique constraint

Revision ID: fix_duplicates
Revises: 0de86e6c3e93
Create Date: 2025-09-09 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fix_duplicates'
down_revision = '0de86e6c3e93'
branch_labels = None
depends_on = None

def upgrade():
    """Remove duplicate post_ids and add unique constraint"""
    
    # First, remove duplicate entries (keep the first occurrence)
    op.execute("""
        DELETE p1 FROM posts p1
        INNER JOIN posts p2 
        WHERE p1.id > p2.id 
        AND p1.post_id = p2.post_id
        AND p1.forum_id = p2.forum_id
    """)
    
    # Now add the unique constraint
    op.create_unique_constraint('uq_posts_post_id', 'posts', ['post_id'])

def downgrade():
    """Remove the unique constraint"""
    op.drop_constraint('uq_posts_post_id', 'posts', type_='unique')