"""add_anomalies_table

Revision ID: 7e6776175c88
Revises: d30dc3838936
Create Date: 2025-08-28 10:03:16.521085

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "7e6776175c88"
down_revision = "d30dc3838936"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create anomalies table for sentiment pattern detection
    op.create_table(
        "anomalies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=False, index=True),
        sa.Column(
            "window_start", sa.DateTime(timezone=True), nullable=False, index=True
        ),
        sa.Column("zscore", sa.Float(), nullable=False),
        sa.Column(
            "direction", sa.String(length=20), nullable=False
        ),  # 'positive' or 'negative'
        sa.Column("post_count", sa.Integer(), nullable=False),
        sa.Column("avg_sentiment", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_anomalies_id"), "anomalies", ["id"], unique=False)
    op.create_index(op.f("ix_anomalies_ticker"), "anomalies", ["ticker"], unique=False)
    op.create_index(
        op.f("ix_anomalies_window_start"), "anomalies", ["window_start"], unique=False
    )


def downgrade() -> None:
    # Drop anomalies table
    op.drop_index(op.f("ix_anomalies_window_start"), table_name="anomalies")
    op.drop_index(op.f("ix_anomalies_ticker"), table_name="anomalies")
    op.drop_index(op.f("ix_anomalies_id"), table_name="anomalies")
    op.drop_table("anomalies")
