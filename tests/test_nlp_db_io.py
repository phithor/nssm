"""
Unit tests for NLP database I/O module.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from nlp.db_io import (
    SentimentDBHandler,
    get_sentiment_statistics,
    get_unscored_posts,
    save_sentiment_scores,
)
from nlp.infer import SentimentResult


class TestSentimentDBHandler:
    """Test SentimentDBHandler class."""

    def test_init(self):
        """Test SentimentDBHandler initialization."""
        session_factory = Mock()
        handler = SentimentDBHandler(session_factory)
        assert handler.session_factory == session_factory

    @patch("nlp.db_io.select")
    @patch("nlp.db_io.func")
    def test_fetch_unscored_posts_success(self, mock_func, mock_select):
        """Test successful fetching of unscored posts."""
        # Mock session and query components
        mock_session = Mock()
        mock_session_factory = Mock(return_value=mock_session)
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        # Mock query execution
        mock_result = Mock()
        mock_row = Mock()
        mock_row.id = 1
        mock_row.text = "Test post"
        mock_row.forum_id = 1
        mock_row.ticker = "TEST"
        mock_row.timestamp = datetime.now(timezone.utc)
        mock_row.author = "Test Author"

        mock_result.mappings.return_value.all.return_value = [mock_row]
        mock_session.execute.return_value = mock_result

        handler = SentimentDBHandler(mock_session_factory)
        posts = handler.fetch_unscored_posts(limit=10)

        assert len(posts) == 1
        assert posts[0]["id"] == 1
        assert posts[0]["text"] == "Test post"

    def test_fetch_unscored_posts_database_error(self):
        """Test handling of database errors when fetching posts."""
        mock_session = Mock()
        mock_session.__enter__ = Mock(side_effect=Exception("DB Error"))
        mock_session_factory = Mock(return_value=mock_session)

        handler = SentimentDBHandler(mock_session_factory)
        posts = handler.fetch_unscored_posts(limit=10)

        assert posts == []

    def test_save_sentiment_results_empty_list(self):
        """Test saving empty sentiment results list."""
        mock_session_factory = Mock()
        handler = SentimentDBHandler(mock_session_factory)

        success_count, error_count = handler.save_sentiment_results([])

        assert success_count == 0
        assert error_count == 0
        # session_factory should not be called for empty list
        mock_session_factory.assert_not_called()

    @patch("nlp.db_io.update")
    def test_save_sentiment_results_success(self, mock_update):
        """Test successful saving of sentiment results."""
        # Mock session and transaction
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_session_factory = Mock(return_value=mock_session)

        # Mock update statement
        mock_update_stmt = Mock()
        mock_update.return_value.where.return_value.values.return_value = (
            mock_update_stmt
        )

        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        # Create test sentiment result
        result = SentimentResult(
            post_id="test_123",
            score=0.75,
            confidence=0.9,
            language="no",
            processing_time=0.1,
            error=None,
        )

        handler = SentimentDBHandler(mock_session_factory)
        success_count, error_count = handler.save_sentiment_results([result])

        assert success_count == 1
        assert error_count == 0

    def test_save_sentiment_results_with_errors(self):
        """Test saving sentiment results when some have errors."""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_session_factory = Mock(return_value=mock_session)

        # Create results - one success, one error
        results = [
            SentimentResult("post1", 0.8, 0.9, "no", 0.1, error=None),
            SentimentResult("post2", 0.0, 0.0, "no", 0.0, error="Processing failed"),
        ]

        handler = SentimentDBHandler(mock_session_factory)
        success_count, error_count = handler.save_sentiment_results(results)

        assert success_count == 0  # Mock doesn't update any rows
        assert error_count == 1  # One result has an error

    @patch("nlp.db_io.select")
    @patch("nlp.db_io.func")
    def test_get_sentiment_stats_success(self, mock_func, mock_select):
        """Test successful retrieval of sentiment statistics."""
        # Mock session
        mock_session = Mock()
        mock_session_factory = Mock(return_value=mock_session)
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        # Mock query result
        mock_result = Mock()
        mock_result.total_posts = 100
        mock_result.analyzed_posts = 80
        mock_result.avg_sentiment = 0.65
        mock_result.min_sentiment = 0.1
        mock_result.max_sentiment = 0.9

        mock_session.execute.return_value.first.return_value = mock_result

        handler = SentimentDBHandler(mock_session_factory)
        stats = handler.get_sentiment_stats(days_back=7)

        assert stats["total_posts"] == 100
        assert stats["analyzed_posts"] == 80
        assert stats["unanalyzed_posts"] == 20
        assert stats["avg_sentiment"] == 0.65
        assert stats["analysis_coverage"] == 0.8

    def test_get_sentiment_stats_no_data(self):
        """Test sentiment stats when no data is available."""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_session_factory = Mock(return_value=mock_session)

        mock_session.execute.return_value.first.return_value = None

        handler = SentimentDBHandler(mock_session_factory)
        stats = handler.get_sentiment_stats(days_back=7)

        assert stats["total_posts"] == 0
        assert stats["analyzed_posts"] == 0
        assert stats["analysis_coverage"] == 0.0

    def test_get_sentiment_stats_error(self):
        """Test handling of errors when getting sentiment stats."""
        mock_session = Mock()
        mock_session.__enter__ = Mock(side_effect=Exception("DB Error"))
        mock_session_factory = Mock(return_value=mock_session)

        handler = SentimentDBHandler(mock_session_factory)
        stats = handler.get_sentiment_stats(days_back=7)

        assert stats == {}

    @patch("nlp.db_io.select")
    @patch("nlp.db_io.func")
    def test_get_posts_needing_analysis_success(self, mock_func, mock_select):
        """Test successful counting of posts needing analysis."""
        mock_session = Mock()
        mock_session_factory = Mock(return_value=mock_session)
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        mock_session.execute.return_value.scalar.return_value = 25

        handler = SentimentDBHandler(mock_session_factory)
        count = handler.get_posts_needing_analysis(min_age_hours=1)

        assert count == 25

    def test_get_posts_needing_analysis_error(self):
        """Test handling of errors when counting posts needing analysis."""
        mock_session = Mock()
        mock_session.__enter__ = Mock(side_effect=Exception("DB Error"))
        mock_session_factory = Mock(return_value=mock_session)

        handler = SentimentDBHandler(mock_session_factory)
        count = handler.get_posts_needing_analysis()

        assert count == 0


class TestConvenienceFunctions:
    """Test convenience functions."""

    @patch("nlp.db_io.SentimentDBHandler")
    def test_get_unscored_posts(self, mock_handler_class):
        """Test get_unscored_posts convenience function."""
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        mock_handler.fetch_unscored_posts.return_value = [{"id": 1, "text": "Test"}]

        posts = get_unscored_posts(Mock(), limit=10, language_hint="no")

        assert len(posts) == 1
        assert posts[0]["id"] == 1
        mock_handler.fetch_unscored_posts.assert_called_once_with(10, "no", None)

    @patch("nlp.db_io.SentimentDBHandler")
    def test_save_sentiment_scores(self, mock_handler_class):
        """Test save_sentiment_scores convenience function."""
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        mock_handler.save_sentiment_results.return_value = (5, 1)

        results = [SentimentResult("test", 0.8, 0.9, "no", 0.1)]
        success_count, error_count = save_sentiment_scores(Mock(), results)

        assert success_count == 5
        assert error_count == 1
        mock_handler.save_sentiment_results.assert_called_once_with(results, None)

    @patch("nlp.db_io.SentimentDBHandler")
    def test_get_sentiment_statistics(self, mock_handler_class):
        """Test get_sentiment_statistics convenience function."""
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        mock_handler.get_sentiment_stats.return_value = {"total_posts": 100}

        stats = get_sentiment_statistics(Mock(), days_back=14, forum_ids=[1, 2])

        assert stats["total_posts"] == 100
        mock_handler.get_sentiment_stats.assert_called_once_with(14, [1, 2])


class TestIntegrationScenarios:
    """Test integration scenarios with realistic data."""

    def test_complete_workflow_simulation(self):
        """Test a complete workflow simulation."""
        # This would be an integration test in a real scenario
        # Here we just verify the components work together

        # Create mock session factory
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_session_factory = Mock(return_value=mock_session)

        # Mock empty result for fetch
        mock_result = Mock()
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        handler = SentimentDBHandler(mock_session_factory)

        # Test fetching posts
        posts = handler.fetch_unscored_posts(limit=10)
        assert posts == []

        # Test saving empty results
        success_count, error_count = handler.save_sentiment_results([])
        assert success_count == 0
        assert error_count == 0

        # Test statistics (mock no data)
        mock_session.execute.return_value.first.return_value = None
        stats = handler.get_sentiment_stats()
        assert stats["total_posts"] == 0
