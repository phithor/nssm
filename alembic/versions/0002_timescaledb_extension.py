"""Add TimescaleDB extension and convert sentiment_agg to hypertable

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
    # Add TimescaleDB extension
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")

    # Convert sentiment_agg table to hypertable
    op.execute(
        """
        SELECT create_hypertable('sentiment_agg', 'interval_start',
                                chunk_time_interval => INTERVAL '1 day',
                                if_not_exists => TRUE);
    """
    )

    # Add compression policy (optional - can be enabled later)
    # op.execute("""
    #     ALTER TABLE sentiment_agg SET (
    #         timescaledb.compress,
    #         timescaledb.compress_segmentby = 'ticker'
    #     );
    # """)


def downgrade() -> None:
    # Remove TimescaleDB extension (this will also remove hypertable)
    op.execute("DROP EXTENSION IF EXISTS timescaledb CASCADE;")
