"""add_analytics_performance_indexes

Revision ID: 3a9ac292e731
Revises: 7e6776175c88
Create Date: 2025-08-28 10:04:04.892314

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "3a9ac292e731"
down_revision = "7e6776175c88"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Performance indexes for analytics queries

    # Posts table - optimize time-based sentiment queries
    op.create_index(
        "ix_posts_timestamp_sentiment",
        "posts",
        ["timestamp", "sentiment_score"],
        unique=False,
    )
    op.create_index(
        "ix_posts_ticker_timestamp", "posts", ["ticker", "timestamp"], unique=False
    )
    op.create_index(
        "ix_posts_sentiment_processed_at",
        "posts",
        ["sentiment_processed_at"],
        unique=False,
    )

    # SentimentAgg table - optimize time-series queries
    op.create_index(
        "ix_sentiment_agg_ticker_interval_end",
        "sentiment_agg",
        ["ticker", "interval_end"],
        unique=False,
    )
    op.create_index(
        "ix_sentiment_agg_interval_start_end",
        "sentiment_agg",
        ["interval_start", "interval_end"],
        unique=False,
    )

    # Anomalies table - optimize time-based anomaly queries
    op.create_index(
        "ix_anomalies_ticker_window_start",
        "anomalies",
        ["ticker", "window_start"],
        unique=False,
    )
    op.create_index("ix_anomalies_direction", "anomalies", ["direction"], unique=False)
    op.create_index("ix_anomalies_zscore", "anomalies", ["zscore"], unique=False)


def downgrade() -> None:
    # Remove performance indexes
    op.drop_index("ix_posts_timestamp_sentiment", table_name="posts")
    op.drop_index("ix_posts_ticker_timestamp", table_name="posts")
    op.drop_index("ix_posts_sentiment_processed_at", table_name="posts")

    op.drop_index("ix_sentiment_agg_ticker_interval_end", table_name="sentiment_agg")
    op.drop_index("ix_sentiment_agg_interval_start_end", table_name="sentiment_agg")

    op.drop_index("ix_anomalies_ticker_window_start", table_name="anomalies")
    op.drop_index("ix_anomalies_direction", table_name="anomalies")
    op.drop_index("ix_anomalies_zscore", table_name="anomalies")
