"""add_sentiment_fields_to_posts

Revision ID: d30dc3838936
Revises: 0002
Create Date: 2025-08-28 09:50:53.179146

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d30dc3838936"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new sentiment analysis fields to posts table
    op.add_column("posts", sa.Column("sentiment_confidence", sa.Float(), nullable=True))
    op.add_column(
        "posts", sa.Column("sentiment_language", sa.String(length=10), nullable=True)
    )
    op.add_column(
        "posts",
        sa.Column("sentiment_processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "posts", sa.Column("sentiment_processing_time", sa.Float(), nullable=True)
    )
    op.add_column("posts", sa.Column("scraper_metadata", sa.Text(), nullable=True))

    # Add indexes for performance
    op.create_index(
        "ix_posts_sentiment_confidence", "posts", ["sentiment_confidence"], unique=False
    )
    op.create_index(
        "ix_posts_sentiment_language", "posts", ["sentiment_language"], unique=False
    )
    op.create_index(
        "ix_posts_sentiment_processed_at",
        "posts",
        ["sentiment_processed_at"],
        unique=False,
    )


def downgrade() -> None:
    # Remove indexes first
    op.drop_index("ix_posts_sentiment_processed_at", table_name="posts")
    op.drop_index("ix_posts_sentiment_language", table_name="posts")
    op.drop_index("ix_posts_sentiment_confidence", table_name="posts")

    # Remove columns
    op.drop_column("posts", "sentiment_processing_time")
    op.drop_column("posts", "sentiment_processed_at")
    op.drop_column("posts", "sentiment_language")
    op.drop_column("posts", "sentiment_confidence")
    op.drop_column("posts", "scraper_metadata")
