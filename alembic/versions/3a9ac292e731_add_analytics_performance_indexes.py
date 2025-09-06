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
    # Performance indexes for analytics queries (idempotent with IF NOT EXISTS)

    # Posts table - optimize time-based sentiment queries
    op.execute("CREATE INDEX IF NOT EXISTS ix_posts_timestamp_sentiment ON posts (timestamp, sentiment_score)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_posts_ticker_timestamp ON posts (ticker, timestamp)")
    # Note: ix_posts_sentiment_processed_at already created in d30dc3838936_add_sentiment_fields_to_posts

    # SentimentAgg table - optimize time-series queries
    op.execute("CREATE INDEX IF NOT EXISTS ix_sentiment_agg_ticker_interval_end ON sentiment_agg (ticker, interval_end)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sentiment_agg_interval_start_end ON sentiment_agg (interval_start, interval_end)")

    # Anomalies table - optimize time-based anomaly queries
    op.execute("CREATE INDEX IF NOT EXISTS ix_anomalies_ticker_window_start ON anomalies (ticker, window_start)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_anomalies_direction ON anomalies (direction)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_anomalies_zscore ON anomalies (zscore)")


def downgrade() -> None:
    # Remove performance indexes
    op.drop_index("ix_posts_timestamp_sentiment", table_name="posts")
    op.drop_index("ix_posts_ticker_timestamp", table_name="posts")
    # Note: ix_posts_sentiment_processed_at dropped in d30dc3838936_add_sentiment_fields_to_posts

    op.drop_index("ix_sentiment_agg_ticker_interval_end", table_name="sentiment_agg")
    op.drop_index("ix_sentiment_agg_interval_start_end", table_name="sentiment_agg")

    op.drop_index("ix_anomalies_ticker_window_start", table_name="anomalies")
    op.drop_index("ix_anomalies_direction", table_name="anomalies")
    op.drop_index("ix_anomalies_zscore", table_name="anomalies")
