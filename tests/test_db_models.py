"""
Unit tests for database models
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Alert, Base, Forum, Post, SentimentAgg


@pytest.fixture
def engine():
    """Create in-memory SQLite engine for testing"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session for testing"""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestForum:
    """Test Forum model"""

    def test_create_forum(self, session):
        """Test creating a forum"""
        forum = Forum(name="Test Forum", url="https://testforum.com")
        session.add(forum)
        session.commit()

        assert forum.id is not None
        assert forum.name == "Test Forum"
        assert forum.url == "https://testforum.com"
        assert forum.created_at is not None

    def test_forum_unique_name(self, session):
        """Test forum name uniqueness constraint"""
        forum1 = Forum(name="Test Forum", url="https://test1.com")
        forum2 = Forum(name="Test Forum", url="https://test2.com")

        session.add(forum1)
        session.commit()

        session.add(forum2)
        with pytest.raises(
            Exception
        ):  # SQLite doesn't enforce unique constraints the same way
            session.commit()

    def test_forum_relationship(self, session):
        """Test forum-posts relationship"""
        forum = Forum(name="Test Forum", url="https://testforum.com")
        session.add(forum)
        session.commit()

        post = Post(
            forum_id=forum.id,
            ticker="AAPL",
            timestamp=datetime.now(),
            author="test_user",
            raw_text="Test post",
            clean_text="Test post",
        )
        session.add(post)
        session.commit()

        assert len(forum.posts) == 1
        assert forum.posts[0].ticker == "AAPL"


class TestPost:
    """Test Post model"""

    def test_create_post(self, session):
        """Test creating a post"""
        forum = Forum(name="Test Forum", url="https://testforum.com")
        session.add(forum)
        session.commit()

        post = Post(
            forum_id=forum.id,
            ticker="AAPL",
            timestamp=datetime.now(),
            author="test_user",
            raw_text="This is a test post about AAPL",
            clean_text="This is a test post about AAPL",
            sentiment_score=0.5,
        )
        session.add(post)
        session.commit()

        assert post.id is not None
        assert post.ticker == "AAPL"
        assert post.sentiment_score == 0.5
        assert post.forum_id == forum.id

    def test_post_foreign_key_constraint(self, session):
        """Test post foreign key constraint"""
        post = Post(
            forum_id=999,  # Non-existent forum ID
            ticker="AAPL",
            timestamp=datetime.now(),
            author="test_user",
            raw_text="Test post",
            clean_text="Test post",
        )

        session.add(post)
        with pytest.raises(Exception):
            session.commit()

    def test_post_sentiment_score_nullable(self, session):
        """Test that sentiment score can be null"""
        forum = Forum(name="Test Forum", url="https://testforum.com")
        session.add(forum)
        session.commit()

        post = Post(
            forum_id=forum.id,
            ticker="AAPL",
            timestamp=datetime.now(),
            author="test_user",
            raw_text="Test post",
            clean_text="Test post",
            sentiment_score=None,
        )
        session.add(post)
        session.commit()

        assert post.sentiment_score is None


class TestSentimentAgg:
    """Test SentimentAgg model"""

    def test_create_sentiment_agg(self, session):
        """Test creating sentiment aggregation"""
        now = datetime.now()
        agg = SentimentAgg(
            ticker="AAPL",
            interval_start=now,
            interval_end=now + timedelta(hours=1),
            avg_score=0.75,
            post_cnt=10,
        )
        session.add(agg)
        session.commit()

        assert agg.id is not None
        assert agg.ticker == "AAPL"
        assert agg.avg_score == 0.75
        assert agg.post_cnt == 10

    def test_sentiment_agg_time_interval(self, session):
        """Test sentiment aggregation time interval logic"""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)

        agg = SentimentAgg(
            ticker="GOOGL",
            interval_start=start_time,
            interval_end=end_time,
            avg_score=0.25,
            post_cnt=5,
        )
        session.add(agg)
        session.commit()

        assert agg.interval_start < agg.interval_end
        assert (agg.interval_end - agg.interval_start) == timedelta(hours=1)


class TestAlert:
    """Test Alert model"""

    def test_create_alert(self, session):
        """Test creating an alert"""
        alert = Alert(
            ticker="TSLA",
            rule="Sentiment score > 0.8",
            triggered_at=datetime.now(),
            is_active=True,
        )
        session.add(alert)
        session.commit()

        assert alert.id is not None
        assert alert.ticker == "TSLA"
        assert alert.rule == "Sentiment score > 0.8"
        assert alert.is_active is True

    def test_alert_default_values(self, session):
        """Test alert default values"""
        alert = Alert(ticker="MSFT", rule="Test rule", triggered_at=datetime.now())
        session.add(alert)
        session.commit()

        assert alert.is_active is True  # Default value
        assert alert.created_at is not None


class TestDatabaseIntegration:
    """Test database integration scenarios"""

    def test_full_workflow(self, session):
        """Test complete workflow: forum -> post -> sentiment -> alert"""
        # Create forum
        forum = Forum(name="Integration Test Forum", url="https://test.com")
        session.add(forum)
        session.commit()

        # Create post
        post = Post(
            forum_id=forum.id,
            ticker="NVDA",
            timestamp=datetime.now(),
            author="integration_user",
            raw_text="NVDA is amazing!",
            clean_text="NVDA is amazing!",
            sentiment_score=0.9,
        )
        session.add(post)
        session.commit()

        # Create sentiment aggregation
        agg = SentimentAgg(
            ticker="NVDA",
            interval_start=datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            ),
            interval_end=datetime.now().replace(
                hour=23, minute=59, second=59, microsecond=999999
            ),
            avg_score=0.9,
            post_cnt=1,
        )
        session.add(agg)
        session.commit()

        # Create alert
        alert = Alert(
            ticker="NVDA",
            rule="High positive sentiment detected",
            triggered_at=datetime.now(),
            is_active=True,
        )
        session.add(alert)
        session.commit()

        # Verify relationships
        assert len(forum.posts) == 1
        assert forum.posts[0].ticker == "NVDA"
        assert forum.posts[0].sentiment_score == 0.9

        # Query by ticker
        nvda_posts = session.query(Post).filter(Post.ticker == "NVDA").all()
        assert len(nvda_posts) == 1

        # Query sentiment aggregation
        nvda_sentiment = (
            session.query(SentimentAgg).filter(SentimentAgg.ticker == "NVDA").first()
        )
        assert nvda_sentiment.avg_score == 0.9

        # Query active alerts
        active_alerts = session.query(Alert).filter(Alert.is_active.is_(True)).all()
        assert len(active_alerts) == 1
        assert active_alerts[0].ticker == "NVDA"
