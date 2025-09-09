"""
SQLAlchemy ORM Models for NSSM Database

This module defines the database schema using SQLAlchemy declarative models
for forums, posts, sentiment aggregation, and alerts.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from . import Base


class Forum(Base):
    """Forum table to store different financial discussion forums"""

    __tablename__ = "forums"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    url = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    posts = relationship("Post", back_populates="forum")


class Post(Base):
    """Post table to store individual forum posts with sentiment analysis"""

    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    forum_id = Column(Integer, ForeignKey("forums.id"), nullable=False, index=True)
    post_id = Column(
        String(255), nullable=False, unique=True, index=True
    )  # External post ID
    ticker = Column(
        String(20), nullable=True, index=True
    )  # Made nullable since not all posts have tickers
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    author = Column(String(255), nullable=False)
    raw_text = Column(Text, nullable=False)
    clean_text = Column(Text, nullable=False)
    url = Column(String(500), nullable=True)  # URL to the original post
    thread_url = Column(
        String(500), nullable=True, index=True
    )  # URL to the thread containing this post
    sentiment_score = Column(Float, nullable=True, index=True)
    sentiment_confidence = Column(Float, nullable=True)  # Model confidence score
    sentiment_language = Column(
        String(10), nullable=True
    )  # Detected language ('no' or 'sv')
    sentiment_processed_at = Column(
        DateTime(timezone=True), nullable=True
    )  # When sentiment was analyzed
    sentiment_processing_time = Column(
        Float, nullable=True
    )  # Time taken for analysis (seconds)
    scraper_metadata = Column(Text, nullable=True)  # JSON metadata from scraper
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    forum = relationship("Forum", back_populates="posts")


class SentimentAgg(Base):
    """Sentiment aggregation table for time-series analysis using TimescaleDB"""

    __tablename__ = "sentiment_agg"

    id = Column(Integer, primary_key=True)
    ticker = Column(String(20), nullable=False, index=True)
    interval_start = Column(DateTime(timezone=True), nullable=False, index=True)
    interval_end = Column(DateTime(timezone=True), nullable=False, index=True)
    avg_score = Column(Float, nullable=False)
    post_cnt = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Index for time-series queries
    __table_args__ = ()


class Anomaly(Base):
    """Anomaly table for storing detected sentiment pattern anomalies"""

    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    window_start = Column(DateTime(timezone=True), nullable=False, index=True)
    zscore = Column(Float, nullable=False)
    direction = Column(String(20), nullable=False)  # 'positive' or 'negative'
    post_count = Column(Integer, nullable=False)
    avg_sentiment = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Alert(Base):
    """Alert table for storing triggered trading alerts"""

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    rule = Column(String(500), nullable=False)
    triggered_at = Column(DateTime(timezone=True), nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class News(Base):
    """News and company announcements table for Scandinavian markets"""

    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    source = Column(
        String(50), nullable=False, index=True
    )  # 'openbb', 'oslobors', 'nasdaq'
    category = Column(
        String(50), nullable=False, default="news", index=True
    )  # 'news', 'filing', 'announcement'
    headline = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)  # For storing announcement HTML content
    link = Column(String(1000), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=False, index=True)
    importance = Column(Float, nullable=True, default=0.5)  # Importance score 0.0-1.0
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at_idx = Column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )  # For query optimization

    # Composite unique constraint to prevent duplicate news entries
    __table_args__ = (
        UniqueConstraint(
            "ticker", "source", "headline", "published_at", name="unique_news_entry"
        ),
    )


class MarketPrice(Base):
    """Market price data table for storing historical price information"""

    __tablename__ = "market_prices"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    volume = Column(Integer, nullable=True)  # Trading volume if available
    high = Column(Float, nullable=True)  # High price for the period
    low = Column(Float, nullable=True)  # Low price for the period
    open_price = Column(Float, nullable=True)  # Opening price for the period
    close_price = Column(
        Float, nullable=True
    )  # Closing price for the period (same as price for intraday)
    source = Column(
        String(50), nullable=False, default="openbb", index=True
    )  # Data source
    interval = Column(
        String(20), nullable=False, default="1H"
    )  # Time interval (1H, 1D, etc.)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Unique constraint to prevent duplicate price entries
    __table_args__ = (
        UniqueConstraint(
            "ticker", "timestamp", "interval", name="unique_ticker_timestamp_interval"
        ),
    )
