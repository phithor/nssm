"""
Dashboard Data Layer Functions

This module provides cached functions for fetching dashboard data from the database.
All functions use Streamlit's caching mechanism for performance optimization.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
from sqlalchemy import and_, desc, func, or_, text
from sqlalchemy.orm import Session

# Import database components
from db import SessionLocal, get_db
from db.models import Anomaly, MarketPrice, News, SentimentAgg


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_buzzing_heatmap_data(start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Get anomaly data for the buzzing stocks heatmap.

    Args:
        start_date: Start date for analysis
        end_date: End date for analysis

    Returns:
        DataFrame with columns: ticker, window_start, zscore, direction, post_count, avg_sentiment
    """
    with SessionLocal() as session:
        try:
            # Query anomalies within the date range
            query = (
                session.query(
                    Anomaly.ticker,
                    Anomaly.window_start,
                    Anomaly.zscore,
                    Anomaly.direction,
                    Anomaly.post_count,
                    Anomaly.avg_sentiment,
                )
                .filter(
                    and_(
                        Anomaly.window_start >= start_date,
                        Anomaly.window_start <= end_date,
                    )
                )
                .order_by(
                    Anomaly.window_start, desc(Anomaly.zscore)  # Most anomalous first
                )
            )

            results = query.all()

            if not results:
                # Return empty DataFrame with correct structure
                return pd.DataFrame(
                    columns=[
                        "ticker",
                        "window_start",
                        "zscore",
                        "direction",
                        "post_count",
                        "avg_sentiment",
                    ]
                )

            # Convert to DataFrame
            df = pd.DataFrame(
                [
                    {
                        "ticker": row.ticker,
                        "window_start": row.window_start,
                        "zscore": row.zscore,
                        "direction": row.direction,
                        "post_count": row.post_count,
                        "avg_sentiment": row.avg_sentiment,
                    }
                    for row in results
                ]
            )

            # Convert window_start to datetime if not already
            df["window_start"] = pd.to_datetime(df["window_start"])

            return df

        except Exception as e:
            st.error(f"Error fetching heatmap data: {str(e)}")
            return pd.DataFrame(
                columns=[
                    "ticker",
                    "window_start",
                    "zscore",
                    "direction",
                    "post_count",
                    "avg_sentiment",
                ]
            )


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_sentiment_price_series(
    ticker: str, start_date: datetime, end_date: datetime
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Get sentiment and price data for a specific ticker.

    Args:
        ticker: Stock ticker symbol
        start_date: Start date for analysis
        end_date: End date for analysis

    Returns:
        Tuple of (sentiment_df, price_df) DataFrames
    """
    with SessionLocal() as session:
        try:
            # Get sentiment data
            sentiment_query = (
                session.query(
                    SentimentAgg.interval_start,
                    SentimentAgg.interval_end,
                    SentimentAgg.avg_score,
                    SentimentAgg.post_cnt,
                )
                .filter(
                    and_(
                        SentimentAgg.ticker == ticker,
                        SentimentAgg.interval_start >= start_date,
                        SentimentAgg.interval_end <= end_date,
                    )
                )
                .order_by(SentimentAgg.interval_start)
            )

            sentiment_results = sentiment_query.all()

            # Get price data
            price_query = (
                session.query(
                    MarketPrice.timestamp,
                    MarketPrice.price,
                    MarketPrice.volume,
                    MarketPrice.high,
                    MarketPrice.low,
                    MarketPrice.interval,
                )
                .filter(
                    and_(
                        MarketPrice.ticker == ticker,
                        MarketPrice.timestamp >= start_date,
                        MarketPrice.timestamp <= end_date,
                    )
                )
                .order_by(MarketPrice.timestamp)
            )

            price_results = price_query.all()

            # Convert sentiment results to DataFrame
            if sentiment_results:
                sentiment_df = pd.DataFrame(
                    [
                        {
                            "timestamp": row.interval_start,
                            "sentiment": row.avg_score,
                            "post_count": row.post_cnt,
                            "interval_end": row.interval_end,
                        }
                        for row in sentiment_results
                    ]
                )
                sentiment_df["timestamp"] = pd.to_datetime(sentiment_df["timestamp"])
            else:
                sentiment_df = pd.DataFrame(
                    columns=["timestamp", "sentiment", "post_count", "interval_end"]
                )

            # Convert price results to DataFrame
            if price_results:
                price_df = pd.DataFrame(
                    [
                        {
                            "timestamp": row.timestamp,
                            "price": row.price,
                            "volume": row.volume,
                            "high": row.high,
                            "low": row.low,
                            "interval": row.interval,
                        }
                        for row in price_results
                    ]
                )
                price_df["timestamp"] = pd.to_datetime(price_df["timestamp"])
            else:
                price_df = pd.DataFrame(
                    columns=["timestamp", "price", "volume", "high", "low", "interval"]
                )

            return sentiment_df, price_df

        except Exception as e:
            st.error(f"Error fetching sentiment/price data for {ticker}: {str(e)}")
            return (
                pd.DataFrame(
                    columns=["timestamp", "sentiment", "post_count", "interval_end"]
                ),
                pd.DataFrame(
                    columns=["timestamp", "price", "volume", "high", "low", "interval"]
                ),
            )


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_news_overlay(
    ticker: str, start_date: datetime, end_date: datetime
) -> pd.DataFrame:
    """
    Get news events for overlay on charts.

    Args:
        ticker: Stock ticker symbol
        start_date: Start date for analysis
        end_date: End date for analysis

    Returns:
        DataFrame with columns: published_at, headline, importance, source, category, link
    """
    with SessionLocal() as session:
        try:
            # Get news data
            query = (
                session.query(
                    News.published_at,
                    News.headline,
                    News.importance,
                    News.source,
                    News.category,
                    News.link,
                    News.summary,
                )
                .filter(
                    and_(
                        News.ticker == ticker,
                        News.published_at >= start_date,
                        News.published_at <= end_date,
                    )
                )
                .order_by(News.published_at)
            )

            results = query.all()

            if not results:
                return pd.DataFrame(
                    columns=[
                        "published_at",
                        "headline",
                        "importance",
                        "source",
                        "category",
                        "link",
                        "summary",
                    ]
                )

            # Convert to DataFrame
            df = pd.DataFrame(
                [
                    {
                        "published_at": row.published_at,
                        "headline": row.headline,
                        "importance": row.importance or 0.5,
                        "source": row.source,
                        "category": row.category,
                        "link": row.link,
                        "summary": row.summary,
                    }
                    for row in results
                ]
            )

            # Convert published_at to datetime if not already
            df["published_at"] = pd.to_datetime(df["published_at"])

            return df

        except Exception as e:
            st.error(f"Error fetching news data for {ticker}: {str(e)}")
            return pd.DataFrame(
                columns=[
                    "published_at",
                    "headline",
                    "importance",
                    "source",
                    "category",
                    "link",
                    "summary",
                ]
            )


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_available_tickers() -> List[str]:
    """
    Get list of all tickers that have data in the system.

    Returns:
        List of unique ticker symbols
    """
    with SessionLocal() as session:
        try:
            # Get tickers from sentiment aggregation (most reliable source)
            sentiment_tickers = session.query(SentimentAgg.ticker).distinct().all()
            sentiment_tickers = [row.ticker for row in sentiment_tickers]

            # Get tickers from market prices
            price_tickers = session.query(MarketPrice.ticker).distinct().all()
            price_tickers = [row.ticker for row in price_tickers]

            # Combine and deduplicate
            all_tickers = list(set(sentiment_tickers + price_tickers))
            return sorted(all_tickers)

        except Exception as e:
            st.error(f"Error fetching available tickers: {str(e)}")
            return []


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_dashboard_stats(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """
    Get overall dashboard statistics.

    Args:
        start_date: Start date for analysis
        end_date: End date for analysis

    Returns:
        Dictionary with dashboard statistics
    """
    with SessionLocal() as session:
        try:
            stats = {}

            # Total posts analyzed
            post_count = (
                session.query(func.count(SentimentAgg.id))
                .filter(
                    and_(
                        SentimentAgg.interval_start >= start_date,
                        SentimentAgg.interval_end <= end_date,
                    )
                )
                .scalar()
            )
            stats["total_posts"] = post_count or 0

            # Unique tickers
            ticker_count = (
                session.query(func.count(func.distinct(SentimentAgg.ticker)))
                .filter(
                    and_(
                        SentimentAgg.interval_start >= start_date,
                        SentimentAgg.interval_end <= end_date,
                    )
                )
                .scalar()
            )
            stats["unique_tickers"] = ticker_count or 0

            # Anomalies detected
            anomaly_count = (
                session.query(func.count(Anomaly.id))
                .filter(
                    and_(
                        Anomaly.window_start >= start_date,
                        Anomaly.window_start <= end_date,
                    )
                )
                .scalar()
            )
            stats["anomalies_detected"] = anomaly_count or 0

            # News items
            news_count = (
                session.query(func.count(News.id))
                .filter(
                    and_(News.published_at >= start_date, News.published_at <= end_date)
                )
                .scalar()
            )
            stats["news_items"] = news_count or 0

            # Average sentiment
            avg_sentiment = (
                session.query(func.avg(SentimentAgg.avg_score))
                .filter(
                    and_(
                        SentimentAgg.interval_start >= start_date,
                        SentimentAgg.interval_end <= end_date,
                    )
                )
                .scalar()
            )
            stats["avg_sentiment"] = round(avg_sentiment, 3) if avg_sentiment else 0.0

            return stats

        except Exception as e:
            st.error(f"Error fetching dashboard stats: {str(e)}")
            return {
                "total_posts": 0,
                "unique_tickers": 0,
                "anomalies_detected": 0,
                "news_items": 0,
                "avg_sentiment": 0.0,
            }
