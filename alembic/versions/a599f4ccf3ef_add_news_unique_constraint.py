"""add_news_unique_constraint

Revision ID: a599f4ccf3ef
Revises: 1d0698fce77f
Create Date: 2025-09-09 13:30:03.071316

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "a599f4ccf3ef"
down_revision = "1d0698fce77f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add unique constraint to prevent duplicate news entries
    # Based on ticker, source, headline, and published_at
    op.create_unique_constraint(
        "unique_news_entry", "news", ["ticker", "source", "headline", "published_at"]
    )


def downgrade() -> None:
    # Remove the unique constraint
    op.drop_constraint("unique_news_entry", "news", type_="unique")
