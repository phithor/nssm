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
    ticker = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    author = Column(String(255), nullable=False)
    raw_text = Column(Text, nullable=False)
    clean_text = Column(Text, nullable=False)
    sentiment_score = Column(Float, nullable=True, index=True)
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
    __table_args__ = {"postgresql_partition_by": "RANGE (interval_start)"}


class Alert(Base):
    """Alert table for storing triggered trading alerts"""

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    rule = Column(String(500), nullable=False)
    triggered_at = Column(DateTime(timezone=True), nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
