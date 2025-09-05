"""add_anomalies_table

Revision ID: 7e6776175c88
Revises: d30dc3838936
Create Date: 2025-08-28 10:03:16.521085

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "7e6776175c88"
down_revision = "d30dc3838936"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create anomalies table for sentiment pattern detection (if not exists)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS anomalies (
            id INTEGER NOT NULL AUTO_INCREMENT,
            ticker VARCHAR(20) NOT NULL,
            window_start DATETIME NOT NULL,
            zscore FLOAT NOT NULL,
            direction VARCHAR(20) NOT NULL,
            post_count INTEGER NOT NULL,
            avg_sentiment FLOAT NOT NULL,
            created_at DATETIME DEFAULT (now()),
            PRIMARY KEY (id)
        )
    """
    )

    # Create indexes if they don't exist
    op.execute("CREATE INDEX IF NOT EXISTS ix_anomalies_ticker ON anomalies (ticker)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_anomalies_window_start "
        "ON anomalies (window_start)"
    )


def downgrade() -> None:
    # Drop anomalies table
    op.drop_index(op.f("ix_anomalies_window_start"), table_name="anomalies")
    op.drop_index(op.f("ix_anomalies_ticker"), table_name="anomalies")
    op.drop_index(op.f("ix_anomalies_id"), table_name="anomalies")
    op.drop_table("anomalies")
