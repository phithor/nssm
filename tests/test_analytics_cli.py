"""
Unit tests for analytics CLI module.

Tests command-line interface functionality.
"""

import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from analytics.__main__ import main


class TestAnalyticsCLI:
    """Test cases for analytics CLI."""

    def test_main_no_args(self):
        """Test main function with no arguments."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0  # Help message printed

    @patch("analytics.__main__.run_aggregation")
    def test_main_aggregate_command(self, mock_run_agg):
        """Test aggregate command."""
        mock_run_agg.return_value = 0

        with patch("sys.argv", ["analytics", "aggregate", "--hours-back", "48"]):
            result = main()

            assert result == 0
            mock_run_agg.assert_called_once()

    @patch("analytics.__main__.run_anomaly_detection")
    def test_main_anomalies_command(self, mock_run_anomalies):
        """Test anomalies command."""
        mock_run_anomalies.return_value = 0

        with patch("sys.argv", ["analytics", "anomalies", "--zscore-threshold", "2.5"]):
            result = main()

            assert result == 0
            mock_run_anomalies.assert_called_once()

    @patch("analytics.__main__.run_combined_pipeline")
    def test_main_pipeline_command(self, mock_run_pipeline):
        """Test pipeline command."""
        mock_run_pipeline.return_value = 0

        with patch("sys.argv", ["analytics", "pipeline", "--hours-back", "24"]):
            result = main()

            assert result == 0
            mock_run_pipeline.assert_called_once()

    @patch("analytics.__main__.run_status")
    def test_main_status_command(self, mock_run_status):
        """Test status command."""
        mock_run_status.return_value = 0

        with patch("sys.argv", ["analytics", "status", "--days-back", "7"]):
            result = main()

            assert result == 0
            mock_run_status.assert_called_once()

    def test_main_unknown_command(self):
        """Test unknown command handling."""
        with patch("sys.argv", ["analytics", "unknown"]):
            result = main()

            assert result == 1

    @patch("analytics.aggregator.SentimentAggregator")
    def test_run_aggregation_success(self, mock_aggregator_class):
        """Test successful aggregation run."""
        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_aggregator.run_aggregation_pipeline.return_value = {
            "success": True,
            "posts_fetched": 100,
            "aggregates_computed": 20,
            "aggregates_persisted": 15,
            "execution_time": 5.2,
        }

        from analytics.__main__ import run_aggregation

        # Create mock args
        args = MagicMock()
        args.hours_back = 24
        args.window_minutes = 5
        args.min_confidence = 0.5

        with patch("builtins.print"):
            result = run_aggregation(args)

        assert result == 0
        mock_aggregator.run_aggregation_pipeline.assert_called_once_with(
            hours_back=24, window_minutes=5, min_confidence=0.5
        )

    @patch("analytics.aggregator.SentimentAggregator")
    def test_run_aggregation_failure(self, mock_aggregator_class):
        """Test aggregation run failure."""
        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_aggregator.run_aggregation_pipeline.return_value = {
            "success": False,
            "error": "Database connection failed",
        }

        from analytics.__main__ import run_aggregation

        args = MagicMock()
        args.hours_back = 24
        args.window_minutes = 5
        args.min_confidence = 0.5

        with patch("builtins.print"):
            result = run_aggregation(args)

        assert result == 1

    @patch("analytics.aggregator.SentimentAggregator")
    def test_run_anomaly_detection_success(self, mock_aggregator_class):
        """Test successful anomaly detection run."""
        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_aggregator.run_anomaly_detection_pipeline.return_value = {
            "success": True,
            "anomalies_detected": 3,
            "anomalies_persisted": 3,
            "execution_time": 2.1,
        }

        from analytics.__main__ import run_anomaly_detection

        args = MagicMock()
        args.hours_back = 24
        args.zscore_threshold = 2.0
        args.min_post_count = 5

        with patch("builtins.print"):
            result = run_anomaly_detection(args)

        assert result == 0
        mock_aggregator.run_anomaly_detection_pipeline.assert_called_once_with(
            hours_back=24, zscore_threshold=2.0, min_post_count=5
        )

    @patch("analytics.aggregator.SentimentAggregator")
    def test_run_status_success(self, mock_aggregator_class):
        """Test successful status run."""
        from datetime import datetime

        import pandas as pd

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        # Mock DataFrame
        mock_df = pd.DataFrame(
            {
                "ticker": ["AAPL", "TSLA"],
                "sentiment_score": [0.5, -0.2],
                "timestamp": [datetime.now(), datetime.now()],
            }
        )
        mock_aggregator.fetch_recent_posts.return_value = mock_df

        from analytics.__main__ import run_status

        args = MagicMock()
        args.days_back = 7

        with patch("builtins.print"):
            result = run_status(args)

        assert result == 0
        mock_aggregator.fetch_recent_posts.assert_called_once_with(hours_back=7 * 24)

    @patch("analytics.aggregator.SentimentAggregator")
    def test_run_combined_pipeline_success(self, mock_aggregator_class):
        """Test successful combined pipeline run."""
        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        mock_aggregator.run_aggregation_pipeline.return_value = {
            "success": True,
            "posts_fetched": 100,
            "aggregates_persisted": 20,
        }
        mock_aggregator.run_anomaly_detection_pipeline.return_value = {
            "success": True,
            "anomalies_persisted": 2,
        }

        from analytics.__main__ import run_combined_pipeline

        args = MagicMock()
        args.hours_back = 24
        args.window_minutes = 5
        args.min_confidence = 0.5
        args.zscore_threshold = 2.0
        args.min_post_count = 5

        with patch("builtins.print"):
            result = run_combined_pipeline(args)

        assert result == 0
        mock_aggregator.run_aggregation_pipeline.assert_called_once()
        mock_aggregator.run_anomaly_detection_pipeline.assert_called_once()
