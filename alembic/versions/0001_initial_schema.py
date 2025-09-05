"""Initial database schema

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create forums table (if not exists)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS forums (
            id INTEGER NOT NULL AUTO_INCREMENT,
            name VARCHAR(255) NOT NULL,
            url VARCHAR(500) NOT NULL,
            created_at DATETIME DEFAULT (now()),
            updated_at DATETIME,
            PRIMARY KEY (id)
        )
    """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_forums_name ON forums (name)")

    # Create posts table (if not exists)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER NOT NULL AUTO_INCREMENT,
            forum_id INTEGER NOT NULL,
            ticker VARCHAR(20) NOT NULL,
            timestamp DATETIME NOT NULL,
            author VARCHAR(255) NOT NULL,
            raw_text TEXT NOT NULL,
            clean_text TEXT NOT NULL,
            sentiment_score FLOAT,
            created_at DATETIME DEFAULT (now()),
            PRIMARY KEY (id),
            FOREIGN KEY (forum_id) REFERENCES forums(id)
        )
    """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_posts_forum_id ON posts (forum_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_posts_ticker ON posts (ticker)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_posts_timestamp ON posts (timestamp)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_posts_sentiment_score ON posts (sentiment_score)"
    )

    # Create sentiment_agg table (if not exists)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sentiment_agg (
            id INTEGER NOT NULL AUTO_INCREMENT,
            ticker VARCHAR(20) NOT NULL,
            interval_start DATETIME NOT NULL,
            interval_end DATETIME NOT NULL,
            avg_score FLOAT NOT NULL,
            post_cnt INTEGER NOT NULL,
            created_at DATETIME DEFAULT (now()),
            PRIMARY KEY (id)
        )
    """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_sentiment_agg_ticker ON sentiment_agg (ticker)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_sentiment_agg_interval_start "
        "ON sentiment_agg (interval_start)"
    )

    # Create alerts table (if not exists)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER NOT NULL AUTO_INCREMENT,
            ticker VARCHAR(20) NOT NULL,
            rule VARCHAR(500) NOT NULL,
            triggered_at DATETIME NOT NULL,
            is_active BOOLEAN,
            created_at DATETIME DEFAULT (now()),
            PRIMARY KEY (id)
        )
    """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_alerts_ticker ON alerts (ticker)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_alerts_triggered_at ON alerts (triggered_at)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_alerts_is_active ON alerts (is_active)")


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
