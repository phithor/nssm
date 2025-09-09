"""add_news_table

Revision ID: 1d0698fce77f
Revises: fix_duplicates
Create Date: 2025-09-09 13:26:52.962463

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "1d0698fce77f"
down_revision = "fix_duplicates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create news table
    op.create_table(
        "news",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False, default="news"),
        sa.Column("headline", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("link", sa.String(length=1000), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("importance", sa.Float(), nullable=True, default=0.5),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "created_at_idx",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for performance
    op.create_index("ix_news_id", "news", ["id"], unique=False)
    op.create_index("ix_news_ticker", "news", ["ticker"], unique=False)
    op.create_index("ix_news_source", "news", ["source"], unique=False)
    op.create_index("ix_news_category", "news", ["category"], unique=False)
    op.create_index("ix_news_published_at", "news", ["published_at"], unique=False)
    op.create_index("ix_news_created_at_idx", "news", ["created_at_idx"], unique=False)


def downgrade() -> None:
    # Drop indexes first
    op.drop_index("ix_news_created_at_idx", table_name="news")
    op.drop_index("ix_news_published_at", table_name="news")
    op.drop_index("ix_news_category", table_name="news")
    op.drop_index("ix_news_source", table_name="news")
    op.drop_index("ix_news_ticker", table_name="news")
    op.drop_index("ix_news_id", table_name="news")

    # Drop table
    op.drop_table("news")
