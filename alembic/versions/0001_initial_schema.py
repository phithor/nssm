"""Initial database schema

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create forums table
    op.create_table(
        "forums",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_forums_id"), "forums", ["id"], unique=False)
    op.create_index(op.f("ix_forums_name"), "forums", ["name"], unique=True)

    # Create posts table
    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("forum_id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("clean_text", sa.Text(), nullable=False),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["forum_id"],
            ["forums.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_posts_id"), "posts", ["id"], unique=False)
    op.create_index(op.f("ix_posts_forum_id"), "posts", ["forum_id"], unique=False)
    op.create_index(op.f("ix_posts_ticker"), "posts", ["ticker"], unique=False)
    op.create_index(op.f("ix_posts_timestamp"), "posts", ["timestamp"], unique=False)
    op.create_index(
        op.f("ix_posts_sentiment_score"), "posts", ["sentiment_score"], unique=False
    )

    # Create sentiment_agg table
    op.create_table(
        "sentiment_agg",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("interval_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interval_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("avg_score", sa.Float(), nullable=False),
        sa.Column("post_cnt", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sentiment_agg_id"), "sentiment_agg", ["id"], unique=False)
    op.create_index(
        op.f("ix_sentiment_agg_ticker"), "sentiment_agg", ["ticker"], unique=False
    )
    op.create_index(
        op.f("ix_sentiment_agg_interval_start"),
        "sentiment_agg",
        ["interval_start"],
        unique=False,
    )

    # Create alerts table
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("rule", sa.String(length=500), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alerts_id"), "alerts", ["id"], unique=False)
    op.create_index(op.f("ix_alerts_ticker"), "alerts", ["ticker"], unique=False)
    op.create_index(
        op.f("ix_alerts_triggered_at"), "alerts", ["triggered_at"], unique=False
    )
    op.create_index(op.f("ix_alerts_is_active"), "alerts", ["is_active"], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f("ix_alerts_is_active"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_triggered_at"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_ticker"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_id"), table_name="alerts")
    op.drop_table("alerts")

    op.drop_index(op.f("ix_sentiment_agg_interval_start"), table_name="sentiment_agg")
    op.drop_index(op.f("ix_sentiment_agg_ticker"), table_name="sentiment_agg")
    op.drop_index(op.f("ix_sentiment_agg_id"), table_name="sentiment_agg")
    op.drop_table("sentiment_agg")

    op.drop_index(op.f("ix_posts_sentiment_score"), table_name="posts")
    op.drop_index(op.f("ix_posts_timestamp"), table_name="posts")
    op.drop_index(op.f("ix_posts_ticker"), table_name="posts")
    op.drop_index(op.f("ix_posts_forum_id"), table_name="posts")
    op.drop_index(op.f("ix_posts_id"), table_name="posts")
    op.drop_table("posts")

    op.drop_index(op.f("ix_forums_name"), table_name="forums")
    op.drop_index(op.f("ix_forums_id"), table_name="forums")
    op.drop_table("forums")
