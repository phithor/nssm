"""MariaDB optimization for sentiment_agg table

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-01 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # For MariaDB, we'll add indexes instead of TimescaleDB hypertables
    # Add index on interval_start for time-based queries
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_sentiment_agg_interval_start ON sentiment_agg (interval_start);"
    )

    # Add index on ticker for ticker-based queries
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_sentiment_agg_ticker ON sentiment_agg (ticker);"
    )

    # Add composite index for common queries
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_sentiment_agg_ticker_interval ON sentiment_agg (ticker, interval_start);"
    )


def downgrade() -> None:
    # Remove the indexes
    op.execute(
        "DROP INDEX IF EXISTS idx_sentiment_agg_interval_start ON sentiment_agg;"
    )
    op.execute("DROP INDEX IF EXISTS idx_sentiment_agg_ticker ON sentiment_agg;")
    op.execute(
        "DROP INDEX IF EXISTS idx_sentiment_agg_ticker_interval ON sentiment_agg;"
    )
