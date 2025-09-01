"""
Unit tests for analytics aggregator module.

Tests sentiment aggregation and anomaly detection functionality.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest

from analytics.aggregator import AggregationWindow, AnomalyResult, SentimentAggregator


class TestSentimentAggregator:
    """Test cases for SentimentAggregator class."""

    @pytest.fixture
    def aggregator(self):
        """Create a SentimentAggregator instance."""
        return SentimentAggregator()

    @pytest.fixture
    def sample_posts_df(self):
        """Create sample posts DataFrame for testing."""
        timestamps = pd.date_range("2024-01-01 10:00:00", periods=20, freq="1min")

        return pd.DataFrame(
            {
                "id": range(1, 21),
                "ticker": ["AAPL"] * 10 + ["TSLA"] * 10,
                "timestamp": timestamps,
                "sentiment_score": np.random.uniform(-1, 1, 20),
                "sentiment_confidence": np.random.uniform(0.5, 1.0, 20),
                "forum_id": [1] * 20,
                "author": [f"user_{i}" for i in range(20)],
            }
        )

    def test_fetch_recent_posts_success(self, aggregator):
        """Test successful fetching of recent posts."""
        with patch.object(aggregator, "session_factory") as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session

            # Mock the query result
            mock_result = Mock()
            mock_posts = [
                (1, "AAPL", datetime.now(), 0.5, 0.8, 1, "user1"),
                (2, "TSLA", datetime.now(), -0.2, 0.9, 1, "user2"),
            ]
            mock_result.fetchall.return_value = mock_posts
            mock_session.execute.return_value = mock_result

            result_df = aggregator.fetch_recent_posts(hours_back=24)

            assert len(result_df) == 2
            assert list(result_df.columns) == [
                "id",
                "ticker",
                "timestamp",
                "sentiment_score",
                "sentiment_confidence",
                "forum_id",
                "author",
            ]
            assert result_df["ticker"].tolist() == ["AAPL", "TSLA"]

    def test_fetch_recent_posts_empty(self, aggregator):
        """Test fetching posts when no data is available."""
        with patch.object(aggregator, "session_factory") as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session

            mock_result = Mock()
            mock_result.fetchall.return_value = []
            mock_session.execute.return_value = mock_result

            result_df = aggregator.fetch_recent_posts(hours_back=24)

            assert result_df.empty

    def test_compute_window_aggregates(self, aggregator, sample_posts_df):
        """Test computation of window aggregates."""
        aggregates = aggregator.compute_window_aggregates(
            sample_posts_df, window_minutes=5
        )

        assert len(aggregates) > 0

        for agg in aggregates:
            assert isinstance(agg, AggregationWindow)
            assert isinstance(agg.start_time, datetime)
            assert isinstance(agg.end_time, datetime)
            assert isinstance(agg.avg_sentiment, (int, float))
            assert agg.post_count > 0
            assert agg.ticker in ["AAPL", "TSLA"]

    def test_compute_window_aggregates_empty_df(self, aggregator):
        """Test computation with empty DataFrame."""
        empty_df = pd.DataFrame()
        aggregates = aggregator.compute_window_aggregates(empty_df)

        assert len(aggregates) == 0

    def test_persist_aggregates_success(self, aggregator):
        """Test successful persistence of aggregates."""
        aggregates = [
            AggregationWindow(
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(minutes=5),
                ticker="AAPL",
                avg_sentiment=0.5,
                post_count=10,
            )
        ]

        with patch.object(aggregator, "session_factory") as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session

            # Mock existing check
            mock_existing = Mock()
            mock_existing.first.return_value = None
            mock_session.execute.return_value = mock_existing

            result = aggregator.persist_aggregates(aggregates)

            assert result == 1
            assert mock_session.add.called
            assert mock_session.commit.called

    def test_persist_aggregates_empty(self, aggregator):
        """Test persistence with no aggregates."""
        result = aggregator.persist_aggregates([])

        assert result == 0

    def test_detect_anomalies_success(self, aggregator):
        """Test successful anomaly detection."""
        with patch.object(aggregator, "session_factory") as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session

            # Mock hourly data with anomalies
            base_time = datetime(2024, 1, 1, 10, 0, 0)
            mock_hourly_data = [
                ("AAPL", base_time, 50, 0.1),
                ("AAPL", base_time + timedelta(hours=1), 51, 0.2),
                ("AAPL", base_time + timedelta(hours=2), 52, 0.3),
                ("AAPL", base_time + timedelta(hours=3), 150, 0.8),  # Anomaly
                ("AAPL", base_time + timedelta(hours=4), 53, 0.1),
            ]

            mock_result = Mock()
            mock_result.fetchall.return_value = mock_hourly_data
            mock_session.execute.return_value = mock_result

            anomalies = aggregator.detect_anomalies(hours_back=24)

            assert len(anomalies) > 0

            for anomaly in anomalies:
                assert isinstance(anomaly, AnomalyResult)
                assert anomaly.zscore > 2.0 or anomaly.zscore < -2.0
                assert anomaly.direction in ["positive", "negative"]

    def test_detect_anomalies_no_data(self, aggregator):
        """Test anomaly detection with no data."""
        with patch.object(aggregator, "session_factory") as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session

            mock_result = Mock()
            mock_result.fetchall.return_value = []
            mock_session.execute.return_value = mock_result

            anomalies = aggregator.detect_anomalies(hours_back=24)

            assert len(anomalies) == 0

    def test_persist_anomalies_success(self, aggregator):
        """Test successful persistence of anomalies."""
        anomalies = [
            AnomalyResult(
                ticker="AAPL",
                window_start=datetime.now(),
                zscore=3.5,
                direction="positive",
                post_count=100,
                avg_sentiment=0.8,
            )
        ]

        with patch.object(aggregator, "session_factory") as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session

            # Mock existing check
            mock_existing = Mock()
            mock_existing.first.return_value = None
            mock_session.execute.return_value = mock_existing

            result = aggregator.persist_anomalies(anomalies)

            assert result == 1
            assert mock_session.add.called
            assert mock_session.commit.called

    def test_run_aggregation_pipeline_success(self, aggregator, sample_posts_df):
        """Test successful execution of aggregation pipeline."""
        with patch.object(aggregator, "fetch_recent_posts") as mock_fetch, patch.object(
            aggregator, "compute_window_aggregates"
        ) as mock_compute, patch.object(
            aggregator, "persist_aggregates"
        ) as mock_persist:

            mock_fetch.return_value = sample_posts_df
            mock_compute.return_value = [
                AggregationWindow(
                    datetime.now(),
                    datetime.now() + timedelta(minutes=5),
                    "AAPL",
                    0.5,
                    10,
                )
            ]
            mock_persist.return_value = 1

            result = aggregator.run_aggregation_pipeline()

            assert result["success"] is True
            assert result["posts_fetched"] == len(sample_posts_df)
            assert result["aggregates_computed"] == 1
            assert result["aggregates_persisted"] == 1

    def test_run_aggregation_pipeline_failure(self, aggregator):
        """Test aggregation pipeline failure."""
        with patch.object(aggregator, "fetch_recent_posts") as mock_fetch:
            mock_fetch.side_effect = Exception("Database error")

            result = aggregator.run_aggregation_pipeline()

            assert result["success"] is False
            assert "Database error" in result["error"]

    def test_run_anomaly_detection_pipeline_success(self, aggregator):
        """Test successful execution of anomaly detection pipeline."""
        with patch.object(aggregator, "detect_anomalies") as mock_detect, patch.object(
            aggregator, "persist_anomalies"
        ) as mock_persist:

            mock_detect.return_value = [
                AnomalyResult("AAPL", datetime.now(), 3.5, "positive", 100, 0.8)
            ]
            mock_persist.return_value = 1

            result = aggregator.run_anomaly_detection_pipeline()

            assert result["success"] is True
            assert result["anomalies_detected"] == 1
            assert result["anomalies_persisted"] == 1

    def test_run_anomaly_detection_pipeline_failure(self, aggregator):
        """Test anomaly detection pipeline failure."""
        with patch.object(aggregator, "detect_anomalies") as mock_detect:
            mock_detect.side_effect = Exception("Detection error")

            result = aggregator.run_anomaly_detection_pipeline()

            assert result["success"] is False
            assert "Detection error" in result["error"]


class TestAggregationWindow:
    """Test cases for AggregationWindow dataclass."""

    def test_aggregation_window_creation(self):
        """Test creating an AggregationWindow instance."""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=5)

        window = AggregationWindow(
            start_time=start_time,
            end_time=end_time,
            ticker="AAPL",
            avg_sentiment=0.5,
            post_count=10,
        )

        assert window.start_time == start_time
        assert window.end_time == end_time
        assert window.ticker == "AAPL"
        assert window.avg_sentiment == 0.5
        assert window.post_count == 10


class TestAnomalyResult:
    """Test cases for AnomalyResult dataclass."""

    def test_anomaly_result_creation(self):
        """Test creating an AnomalyResult instance."""
        window_start = datetime.now()

        anomaly = AnomalyResult(
            ticker="AAPL",
            window_start=window_start,
            zscore=3.5,
            direction="positive",
            post_count=100,
            avg_sentiment=0.8,
        )

        assert anomaly.ticker == "AAPL"
        assert anomaly.window_start == window_start
        assert anomaly.zscore == 3.5
        assert anomaly.direction == "positive"
        assert anomaly.post_count == 100
        assert anomaly.avg_sentiment == 0.8
