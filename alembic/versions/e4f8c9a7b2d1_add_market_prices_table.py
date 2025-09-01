"""add_market_prices_table

Revision ID: e4f8c9a7b2d1
Revises: d30dc3838936
Create Date: 2025-08-28 10:15:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "e4f8c9a7b2d1"
down_revision = "d30dc3838936"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create market_prices table
    op.create_table(
        "market_prices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("volume", sa.Integer(), nullable=True),
        sa.Column("high", sa.Float(), nullable=True),
        sa.Column("low", sa.Float(), nullable=True),
        sa.Column("open_price", sa.Float(), nullable=True),
        sa.Column("close_price", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False, default="openbb"),
        sa.Column("interval", sa.String(length=20), nullable=False, default="1H"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ticker", "timestamp", "interval", name="unique_ticker_timestamp_interval"
        ),
    )

    # Create indexes for performance
    op.create_index("ix_market_prices_id", "market_prices", ["id"], unique=False)
    op.create_index(
        "ix_market_prices_ticker", "market_prices", ["ticker"], unique=False
    )
    op.create_index(
        "ix_market_prices_timestamp", "market_prices", ["timestamp"], unique=False
    )
    op.create_index(
        "ix_market_prices_source", "market_prices", ["source"], unique=False
    )

    # Create TimescaleDB hypertable if TimescaleDB is enabled
    # This will be done via a separate migration if TS is enabled


def downgrade() -> None:
    # Drop indexes first
    op.drop_index("ix_market_prices_source", table_name="market_prices")
    op.drop_index("ix_market_prices_timestamp", table_name="market_prices")
    op.drop_index("ix_market_prices_ticker", table_name="market_prices")
    op.drop_index("ix_market_prices_id", table_name="market_prices")

    # Drop table
    op.drop_table("market_prices")
