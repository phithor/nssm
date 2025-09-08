"""
Sentiment Aggregation and Anomaly Detection Module

This module provides functionality to:
1. Query recent posts with sentiment scores
2. Aggregate sentiment data into time windows
3. Detect anomalies in post volume and sentiment patterns
4. Store aggregated results in the database
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy import and_, desc, func, select
from sqlalchemy.exc import SQLAlchemyError

from db import SessionLocal
from db.models import Anomaly, Post, SentimentAgg

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class AggregationWindow:
    """Represents a time window for sentiment aggregation."""

    start_time: datetime
    end_time: datetime
    ticker: str
    avg_sentiment: float
    post_count: int


@dataclass
class AnomalyResult:
    """Represents a detected anomaly in sentiment patterns."""

    ticker: str
    window_start: datetime
    zscore: float
    direction: str  # 'positive' or 'negative'
    post_count: int
    avg_sentiment: float


class SentimentAggregator:
    """Handles sentiment aggregation and anomaly detection workflows."""

    def __init__(self, session_factory=None):
        """
        Initialize the sentiment aggregator.

        Args:
            session_factory: Optional custom session factory, defaults to SessionLocal
        """
        self.session_factory = session_factory or SessionLocal

    def fetch_recent_posts(
        self,
        hours_back: int = 24,
        min_sentiment_confidence: float = 0.5,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Fetch posts from the last N hours that have sentiment scores.

        Args:
            hours_back: Number of hours to look back
            min_sentiment_confidence: Minimum confidence score for posts to include
            limit: Optional limit on number of posts to fetch

        Returns:
            DataFrame with columns: id, ticker, timestamp, sentiment_score,
            sentiment_confidence, forum_id, author
        """
        cutoff_time = datetime.now() - timedelta(hours=hours_back)

        try:
            with self.session_factory() as session:
                # Build query for recent posts with sentiment scores
                query = (
                    select(
                        Post.id,
                        Post.ticker,
                        Post.timestamp,
                        Post.sentiment_score,
                        Post.sentiment_confidence,
                        Post.forum_id,
                        Post.author,
                    )
                    .where(
                        and_(
                            Post.timestamp >= cutoff_time,
                            Post.sentiment_score.isnot(None),
                            Post.sentiment_confidence >= min_sentiment_confidence,
                            Post.ticker.isnot(None),  # Only posts with tickers
                        )
                    )
                    .order_by(desc(Post.timestamp))
                )

                if limit:
                    query = query.limit(limit)

                # Execute query and convert to DataFrame
                result = session.execute(query)
                posts_data = result.fetchall()

                if not posts_data:
                    logger.warning(f"No posts found in the last {hours_back} hours")
                    return pd.DataFrame()

                # Convert to DataFrame
                df = pd.DataFrame(
                    posts_data,
                    columns=[
                        "id",
                        "ticker",
                        "timestamp",
                        "sentiment_score",
                        "sentiment_confidence",
                        "forum_id",
                        "author",
                    ],
                )

                # Ensure timestamp is datetime
                df["timestamp"] = pd.to_datetime(df["timestamp"])

                logger.info(f"Fetched {len(df)} posts from the last {hours_back} hours")
                return df

        except SQLAlchemyError as e:
            logger.error(f"Database error fetching recent posts: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching recent posts: {e}")
            raise

    def compute_window_aggregates(
        self, posts_df: pd.DataFrame, window_minutes: int = 5
    ) -> List[AggregationWindow]:
        """
        Compute sentiment aggregates for time windows.

        Args:
            posts_df: DataFrame of posts with sentiment scores
            window_minutes: Size of time windows in minutes

        Returns:
            List of AggregationWindow objects
        """
        if posts_df.empty:
            logger.warning("No posts data to aggregate")
            return []

        try:
            # Set timestamp as index for resampling
            df = posts_df.set_index("timestamp")

            # Group by ticker and resample to window_minutes intervals
            window_aggs = []

            for ticker in df["ticker"].unique():
                ticker_data = df[df["ticker"] == ticker]

                if ticker_data.empty:
                    continue

                # Resample to window_minutes intervals
                resampled = (
                    ticker_data.resample(f"{window_minutes}min")
                    .agg({"sentiment_score": "mean", "id": "count"})  # Post count
                    .rename(columns={"id": "post_count"})
                )

                # Drop windows with no data
                resampled = resampled[resampled["post_count"] > 0]

                for timestamp, row in resampled.iterrows():
                    window = AggregationWindow(
                        start_time=timestamp,
                        end_time=timestamp + timedelta(minutes=window_minutes),
                        ticker=ticker,
                        avg_sentiment=row["sentiment_score"],
                        post_count=int(row["post_count"]),
                    )
                    window_aggs.append(window)

            logger.info(f"Computed {len(window_aggs)} aggregation windows")
            return window_aggs

        except Exception as e:
            logger.error(f"Error computing window aggregates: {e}")
            raise

    def persist_aggregates(self, aggregates: List[AggregationWindow]) -> int:
        """
        Persist aggregation results to the sentiment_agg table.

        Args:
            aggregates: List of AggregationWindow objects to store

        Returns:
            Number of records inserted
        """
        if not aggregates:
            logger.warning("No aggregates to persist")
            return 0

        try:
            with self.session_factory() as session:
                inserted_count = 0

                for agg in aggregates:
                    # Check if this exact window already exists
                    existing = session.execute(
                        select(SentimentAgg).where(
                            and_(
                                SentimentAgg.ticker == agg.ticker,
                                SentimentAgg.interval_start == agg.start_time,
                                SentimentAgg.interval_end == agg.end_time,
                            )
                        )
                    ).first()

                    if existing:
                        # Update existing record
                        existing[0].avg_score = agg.avg_sentiment
                        existing[0].post_cnt = agg.post_count
                        logger.debug(
                            f"Updated existing aggregate for {agg.ticker} at {agg.start_time}"
                        )
                    else:
                        # Create new record
                        sentiment_agg = SentimentAgg(
                            ticker=agg.ticker,
                            interval_start=agg.start_time,
                            interval_end=agg.end_time,
                            avg_score=agg.avg_sentiment,
                            post_cnt=agg.post_count,
                        )
                        session.add(sentiment_agg)
                        inserted_count += 1
                        logger.debug(
                            f"Added new aggregate for {agg.ticker} at {agg.start_time}"
                        )

                session.commit()
                logger.info(
                    f"Persisted {inserted_count} new aggregates, updated {len(aggregates) - inserted_count} existing"
                )
                return inserted_count

        except SQLAlchemyError as e:
            logger.error(f"Database error persisting aggregates: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error persisting aggregates: {e}")
            raise

    def run_aggregation_pipeline(
        self, hours_back: int = 24, window_minutes: int = 5, min_confidence: float = 0.5
    ) -> Dict[str, Any]:
        """
        Run the complete aggregation pipeline.

        Args:
            hours_back: Hours to look back for posts
            window_minutes: Window size in minutes
            min_confidence: Minimum sentiment confidence

        Returns:
            Dictionary with pipeline results and statistics
        """
        start_time = time.time()

        try:
            # Step 1: Fetch recent posts
            posts_df = self.fetch_recent_posts(
                hours_back=hours_back, min_sentiment_confidence=min_confidence
            )

            if posts_df.empty:
                return {
                    "success": True,
                    "posts_fetched": 0,
                    "aggregates_computed": 0,
                    "aggregates_persisted": 0,
                    "execution_time": time.time() - start_time,
                }

            # Step 2: Compute window aggregates
            aggregates = self.compute_window_aggregates(
                posts_df=posts_df, window_minutes=window_minutes
            )

            # Step 3: Persist aggregates
            persisted_count = self.persist_aggregates(aggregates)

            execution_time = time.time() - start_time

            result = {
                "success": True,
                "posts_fetched": len(posts_df),
                "aggregates_computed": len(aggregates),
                "aggregates_persisted": persisted_count,
                "execution_time": execution_time,
                "posts_per_second": (
                    len(posts_df) / execution_time if execution_time > 0 else 0
                ),
            }

            logger.info(
                f"Aggregation pipeline completed in {execution_time:.2f}s: "
                f"{result['posts_fetched']} posts -> {result['aggregates_computed']} windows"
            )

            return result

        except Exception as e:
            logger.error(f"Aggregation pipeline failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time,
            }

    def detect_anomalies(
        self,
        hours_back: int = 24,
        zscore_threshold: float = 2.0,
        min_post_count: int = 5,
    ) -> List[AnomalyResult]:
        """
        Detect anomalies in post volume using z-score analysis.

        Args:
            hours_back: Hours of historical data to analyze
            zscore_threshold: Minimum z-score to consider as anomaly
            min_post_count: Minimum posts in a window to consider for analysis

        Returns:
            List of detected anomalies
        """
        try:
            with self.session_factory() as session:
                # Get recent sentiment aggregates for z-score calculation
                cutoff_time = datetime.now() - timedelta(hours=hours_back)

                # Query recent sentiment aggregates grouped by ticker and hour
                # Use DATE_FORMAT for MySQL/MariaDB compatibility instead of PostgreSQL's date_trunc
                hour_trunc = func.date_format(SentimentAgg.interval_start, "%Y-%m-%d %H:00:00").label("hour")
                
                result = session.execute(
                    select(
                        SentimentAgg.ticker,
                        hour_trunc,
                        func.sum(SentimentAgg.post_cnt).label("total_posts"),
                        func.avg(SentimentAgg.avg_score).label("avg_sentiment"),
                    )
                    .where(SentimentAgg.interval_start >= cutoff_time)
                    .group_by(
                        SentimentAgg.ticker,
                        hour_trunc,
                    )
                    .order_by(
                        SentimentAgg.ticker,
                        hour_trunc,
                    )
                )

                hourly_data = result.fetchall()

                if not hourly_data:
                    logger.warning(
                        f"No sentiment aggregate data found in the last {hours_back} hours"
                    )
                    return []

                # Convert to DataFrame for analysis
                df = pd.DataFrame(
                    hourly_data,
                    columns=["ticker", "hour", "total_posts", "avg_sentiment"],
                )
                df["hour"] = pd.to_datetime(df["hour"])

                anomalies = []

                # Analyze each ticker separately
                for ticker in df["ticker"].unique():
                    ticker_data = df[df["ticker"] == ticker].copy()

                    if len(ticker_data) < 2:  # Need at least 2 data points for z-score
                        continue

                    # Calculate mean and std of post counts
                    post_counts = ticker_data["total_posts"].values
                    mean_posts = post_counts.mean()
                    std_posts = post_counts.std()

                    if std_posts == 0:  # No variation, skip
                        continue

                    # Calculate z-scores for each hour
                    ticker_data["zscore"] = (
                        ticker_data["total_posts"] - mean_posts
                    ) / std_posts

                    # Find anomalies
                    anomaly_rows = ticker_data[
                        (ticker_data["zscore"].abs() > zscore_threshold)
                        & (ticker_data["total_posts"] >= min_post_count)
                    ]

                    for _, row in anomaly_rows.iterrows():
                        anomaly = AnomalyResult(
                            ticker=ticker,
                            window_start=row["hour"],
                            zscore=row["zscore"],
                            direction="positive" if row["zscore"] > 0 else "negative",
                            post_count=int(row["total_posts"]),
                            avg_sentiment=row["avg_sentiment"],
                        )
                        anomalies.append(anomaly)

                logger.info(
                    f"Detected {len(anomalies)} anomalies across {len(df['ticker'].unique())} tickers"
                )
                return anomalies

        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            raise

    def persist_anomalies(self, anomalies: List[AnomalyResult]) -> int:
        """
        Persist detected anomalies to the anomalies table.

        Args:
            anomalies: List of AnomalyResult objects to store

        Returns:
            Number of anomalies inserted
        """
        if not anomalies:
            logger.warning("No anomalies to persist")
            return 0

        try:
            with self.session_factory() as session:
                inserted_count = 0

                for anomaly in anomalies:
                    # Check if this anomaly already exists
                    existing = session.execute(
                        select(Anomaly).where(
                            and_(
                                Anomaly.ticker == anomaly.ticker,
                                Anomaly.window_start == anomaly.window_start,
                            )
                        )
                    ).first()

                    if not existing:
                        # Create new anomaly record
                        anomaly_record = Anomaly(
                            ticker=anomaly.ticker,
                            window_start=anomaly.window_start,
                            zscore=anomaly.zscore,
                            direction=anomaly.direction,
                            post_count=anomaly.post_count,
                            avg_sentiment=anomaly.avg_sentiment,
                        )
                        session.add(anomaly_record)
                        inserted_count += 1
                        logger.debug(
                            f"Added anomaly for {anomaly.ticker} at {anomaly.window_start}"
                        )

                session.commit()
                logger.info(f"Persisted {inserted_count} new anomalies")
                return inserted_count

        except SQLAlchemyError as e:
            logger.error(f"Database error persisting anomalies: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error persisting anomalies: {e}")
            raise

    def run_anomaly_detection_pipeline(
        self,
        hours_back: int = 24,
        zscore_threshold: float = 2.0,
        min_post_count: int = 5,
    ) -> Dict[str, Any]:
        """
        Run the complete anomaly detection pipeline.

        Args:
            hours_back: Hours of historical data to analyze
            zscore_threshold: Minimum z-score for anomaly detection
            min_post_count: Minimum posts to consider for analysis

        Returns:
            Dictionary with pipeline results and statistics
        """
        start_time = time.time()

        try:
            # Step 1: Detect anomalies
            anomalies = self.detect_anomalies(
                hours_back=hours_back,
                zscore_threshold=zscore_threshold,
                min_post_count=min_post_count,
            )

            # Step 2: Persist anomalies
            persisted_count = self.persist_anomalies(anomalies)

            execution_time = time.time() - start_time

            result = {
                "success": True,
                "anomalies_detected": len(anomalies),
                "anomalies_persisted": persisted_count,
                "execution_time": execution_time,
                "anomalies_per_second": (
                    len(anomalies) / execution_time if execution_time > 0 else 0
                ),
            }

            logger.info(
                f"Anomaly detection pipeline completed in {execution_time:.2f}s: "
                f"{result['anomalies_detected']} anomalies detected"
            )

            return result

        except Exception as e:
            logger.error(f"Anomaly detection pipeline failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time,
            }
