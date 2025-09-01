"""
Unit tests for NLP batch inference module.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from nlp.infer import (
    BatchInferenceResult,
    SentimentAnalyzer,
    SentimentResult,
    analyze_sentiment,
    analyze_single_post,
)


class TestSentimentResult:
    """Test SentimentResult dataclass."""

    def test_sentiment_result_creation(self):
        """Test creating a SentimentResult instance."""
        result = SentimentResult(
            post_id="test_123",
            score=0.75,
            confidence=0.8,
            language="no",
            processing_time=0.123,
            error=None,
        )

        assert result.post_id == "test_123"
        assert result.score == 0.75
        assert result.confidence == 0.8
        assert result.language == "no"
        assert result.processing_time == 0.123
        assert result.error is None

    def test_sentiment_result_with_error(self):
        """Test SentimentResult with error message."""
        result = SentimentResult(
            post_id="test_456",
            score=0.0,
            confidence=0.0,
            language="no",
            processing_time=0.0,
            error="Processing failed",
        )

        assert result.error == "Processing failed"
        assert result.score == 0.0
        assert result.confidence == 0.0


class TestBatchInferenceResult:
    """Test BatchInferenceResult dataclass."""

    def test_batch_inference_result_creation(self):
        """Test creating a BatchInferenceResult instance."""
        results = [
            SentimentResult("post1", 0.8, 0.9, "no", 0.1),
            SentimentResult("post2", 0.3, 0.7, "sv", 0.1),
        ]

        batch_result = BatchInferenceResult(
            results=results,
            batch_size=2,
            processing_time=0.25,
            success_count=2,
            error_count=0,
        )

        assert len(batch_result.results) == 2
        assert batch_result.batch_size == 2
        assert batch_result.processing_time == 0.25
        assert batch_result.success_count == 2
        assert batch_result.error_count == 0


class TestSentimentAnalyzer:
    """Test SentimentAnalyzer class."""

    def test_init(self):
        """Test SentimentAnalyzer initialization."""
        analyzer = SentimentAnalyzer(batch_size=8, max_length=256)

        assert analyzer.batch_size == 8
        assert analyzer.max_length == 256
        assert analyzer._model_cache == {}

    def test_init_default_values(self):
        """Test SentimentAnalyzer initialization with default values."""
        analyzer = SentimentAnalyzer()

        assert analyzer.batch_size == 16
        assert analyzer.max_length == 512
        assert analyzer._model_cache == {}

    @patch("nlp.infer.detect_lang")
    def test_group_posts_by_language(self, mock_detect_lang):
        """Test grouping posts by detected language."""
        analyzer = SentimentAnalyzer()

        # Mock language detection
        mock_detect_lang.side_effect = ["no", "sv", "no", "sv"]

        posts = [
            {"id": "1", "text": "Norwegian text"},
            {"id": "2", "text": "Swedish text"},
            {"id": "3", "text": "More Norwegian"},
            {"id": "4", "text": "More Swedish"},
        ]

        groups = analyzer._group_posts_by_language(posts)

        assert "no" in groups
        assert "sv" in groups
        assert len(groups["no"]) == 2
        assert len(groups["sv"]) == 2

    @patch("nlp.infer.detect_lang")
    def test_group_posts_empty_text(self, mock_detect_lang):
        """Test grouping posts with empty text."""
        analyzer = SentimentAnalyzer()

        posts = [
            {"id": "1", "text": ""},
            {"id": "2", "text": "   "},
            {"id": "3", "text": "\n\t"},
        ]

        groups = analyzer._group_posts_by_language(posts)

        assert "no" in groups  # Empty texts default to Norwegian
        assert len(groups["no"]) == 3
        # detect_lang should not be called for empty texts
        mock_detect_lang.assert_not_called()

    @patch("nlp.infer.detect_lang")
    def test_group_posts_detection_error(self, mock_detect_lang):
        """Test grouping posts when language detection fails."""
        analyzer = SentimentAnalyzer()

        mock_detect_lang.side_effect = Exception("Detection failed")

        posts = [{"id": "1", "text": "Some text"}]

        groups = analyzer._group_posts_by_language(posts)

        assert "no" in groups  # Should default to Norwegian on error
        assert len(groups["no"]) == 1

    @patch("nlp.infer.get_model")
    @patch("nlp.infer.clean_text")
    def test_analyze_language_batch_success(self, mock_clean_text, mock_get_model):
        """Test successful language batch analysis."""
        analyzer = SentimentAnalyzer()

        # Mock model and tokenizer
        mock_tokenizer = Mock()
        mock_model = Mock()
        mock_model.device = "cpu"
        mock_get_model.return_value = (mock_tokenizer, mock_model)

        # Mock preprocessing
        mock_clean_text.return_value = "cleaned text"

        # Mock model outputs
        mock_outputs = Mock()
        mock_outputs.logits = Mock()
        mock_model.return_value = mock_outputs

        # Mock torch operations
        with patch("torch.softmax") as mock_softmax, patch("torch.sort") as mock_sort:

            mock_softmax.return_value = Mock()
            mock_softmax.return_value.__getitem__ = Mock(return_value=Mock())
            mock_softmax.return_value.__getitem__.return_value.cpu.return_value.numpy.return_value = [
                0.8,
                0.6,
            ]

            mock_sort.return_value = (Mock(), Mock())
            mock_sort.return_value[0].__getitem__ = Mock(return_value=Mock())
            mock_sort.return_value[0].__getitem__.return_value.__sub__ = Mock(
                return_value=Mock()
            )
            mock_sort.return_value[
                0
            ].__getitem__.return_value.__sub__.return_value.cpu.return_value.numpy.return_value = [
                0.3,
                0.2,
            ]

            posts = [
                {"id": "post1", "text": "Great news!"},
                {"id": "post2", "text": "Bad news!"},
            ]

            results = analyzer._analyze_language_batch("no", posts)

            assert len(results) == 2
            assert results[0].post_id == "post1"
            assert results[0].language == "no"
            assert results[0].error is None
            assert results[1].post_id == "post2"
            assert results[1].language == "no"
            assert results[1].error is None

    @patch("nlp.infer.get_model")
    def test_analyze_language_batch_model_error(self, mock_get_model):
        """Test language batch analysis when model loading fails."""
        analyzer = SentimentAnalyzer()

        mock_get_model.side_effect = Exception("Model loading failed")

        posts = [{"id": "post1", "text": "Some text"}]

        results = analyzer._analyze_language_batch("no", posts)

        assert len(results) == 1
        assert results[0].post_id == "post1"
        assert results[0].error == "Model loading failed"

    @patch("nlp.infer.clean_text")
    def test_analyze_single_batch_preprocessing_error(self, mock_clean_text):
        """Test single batch analysis when preprocessing fails."""
        analyzer = SentimentAnalyzer()

        mock_tokenizer = Mock()
        mock_model = Mock()

        mock_clean_text.side_effect = Exception("Preprocessing failed")

        posts = [{"id": "post1", "text": "Some text"}]

        results = analyzer._analyze_single_batch(
            mock_tokenizer, mock_model, posts, "no"
        )

        assert len(results) == 1
        assert results[0].post_id == "post1"
        assert "Preprocessing failed" in results[0].error

    def test_analyze_single_batch_empty_texts(self):
        """Test single batch analysis with empty texts."""
        analyzer = SentimentAnalyzer()

        mock_tokenizer = Mock()
        mock_model = Mock()

        posts = [{"id": "post1", "text": ""}, {"id": "post2", "text": "   "}]

        results = analyzer._analyze_single_batch(
            mock_tokenizer, mock_model, posts, "no"
        )

        assert len(results) == 2
        for result in results:
            assert result.score == 0.5  # Neutral score for empty text
            assert result.confidence == 0.0
            assert "Empty text after preprocessing" in result.error

    @patch("nlp.infer.detect_lang")
    @patch("nlp.infer.SentimentAnalyzer._analyze_language_batch")
    def test_analyze_batch_success(self, mock_analyze_lang_batch, mock_detect_lang):
        """Test successful batch analysis."""
        analyzer = SentimentAnalyzer()

        # Mock language detection
        mock_detect_lang.side_effect = ["no", "sv", "no"]

        # Mock language batch analysis
        mock_analyze_lang_batch.return_value = [
            SentimentResult("post1", 0.8, 0.9, "no", 0.1),
            SentimentResult("post2", 0.6, 0.8, "no", 0.1),
        ]

        posts = [
            {"id": "post1", "text": "Norwegian text"},
            {"id": "post2", "text": "Swedish text"},
            {"id": "post3", "text": "More Norwegian"},
        ]

        result = analyzer.analyze_batch(posts)

        assert isinstance(result, BatchInferenceResult)
        assert result.batch_size == 3
        assert result.success_count == 2  # Mock returns 2 results for 'no' group
        assert result.error_count == 1  # One post in 'sv' group not processed by mock

    @patch("nlp.infer.detect_lang")
    @patch("nlp.infer.SentimentAnalyzer._analyze_language_batch")
    def test_analyze_batch_with_errors(self, mock_analyze_lang_batch, mock_detect_lang):
        """Test batch analysis when language batch processing fails."""
        analyzer = SentimentAnalyzer()

        # Mock language detection
        mock_detect_lang.return_value = "no"

        # Mock language batch analysis to raise exception
        mock_analyze_lang_batch.side_effect = Exception("Processing failed")

        posts = [{"id": "post1", "text": "Some text"}]

        result = analyzer.analyze_batch(posts)

        assert result.error_count == 1
        assert result.success_count == 0
        assert len(result.results) == 1
        assert result.results[0].error == "Processing failed"

    @patch("nlp.infer.detect_lang")
    def test_analyze_batch_empty_posts(self, mock_detect_lang):
        """Test batch analysis with empty post list."""
        analyzer = SentimentAnalyzer()

        result = analyzer.analyze_batch([])

        assert result.batch_size == 0
        assert result.success_count == 0
        assert result.error_count == 0
        assert len(result.results) == 0


class TestConvenienceFunctions:
    """Test convenience functions."""

    @patch("nlp.infer.SentimentAnalyzer")
    def test_analyze_sentiment(self, mock_analyzer_class):
        """Test analyze_sentiment convenience function."""
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        mock_result = BatchInferenceResult(
            results=[],
            batch_size=2,
            processing_time=0.1,
            success_count=2,
            error_count=0,
        )
        mock_analyzer.analyze_batch.return_value = mock_result

        posts = [{"id": "post1", "text": "Text 1"}, {"id": "post2", "text": "Text 2"}]

        result = analyze_sentiment(posts, locale_hint="no", batch_size=8)

        assert result == mock_result
        mock_analyzer_class.assert_called_once_with(batch_size=8)
        mock_analyzer.analyze_batch.assert_called_once_with(posts, "no")

    @patch("nlp.infer.analyze_sentiment")
    def test_analyze_single_post_success(self, mock_analyze_sentiment):
        """Test analyze_single_post with successful result."""
        mock_result = BatchInferenceResult(
            results=[SentimentResult("test_id", 0.7, 0.8, "no", 0.1)],
            batch_size=1,
            processing_time=0.1,
            success_count=1,
            error_count=0,
        )
        mock_analyze_sentiment.return_value = mock_result

        result = analyze_single_post("test_id", "Test text", "no")

        assert result.post_id == "test_id"
        assert result.score == 0.7
        assert result.confidence == 0.8
        assert result.language == "no"

    @patch("nlp.infer.analyze_sentiment")
    def test_analyze_single_post_no_results(self, mock_analyze_sentiment):
        """Test analyze_single_post when no results are returned."""
        mock_result = BatchInferenceResult(
            results=[],
            batch_size=1,
            processing_time=0.1,
            success_count=0,
            error_count=1,
        )
        mock_analyze_sentiment.return_value = mock_result

        result = analyze_single_post("test_id", "Test text")

        assert result.post_id == "test_id"
        assert result.language == "unknown"
        assert result.error == "Analysis failed"
