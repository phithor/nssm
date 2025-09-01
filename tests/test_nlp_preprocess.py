"""
Unit tests for NLP text preprocessing module.
"""

import json
import tempfile
from pathlib import Path

import pytest

from nlp.preprocess import DEFAULT_FINANCE_SLANG, TextPreprocessor, clean_text


class TestTextPreprocessor:
    """Test cases for the TextPreprocessor class."""

    def test_init_without_slang_dict(self):
        """Test initialization without slang dictionary."""
        preprocessor = TextPreprocessor()
        assert preprocessor.slang_dict == {}
        assert hasattr(preprocessor, "url_pattern")
        assert hasattr(preprocessor, "emoji_pattern")

    def test_init_with_slang_dict(self):
        """Test initialization with slang dictionary."""
        slang_dict = {"test": "replacement"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(slang_dict, f)
            temp_path = Path(f.name)

        try:
            preprocessor = TextPreprocessor(temp_path)
            assert preprocessor.slang_dict == slang_dict
        finally:
            temp_path.unlink()

    def test_init_with_invalid_slang_dict(self):
        """Test initialization with invalid slang dictionary file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json")
            temp_path = Path(f.name)

        try:
            preprocessor = TextPreprocessor(temp_path)
            assert preprocessor.slang_dict == {}
        finally:
            temp_path.unlink()


class TestCleanText:
    """Test cases for the clean_text method."""

    def test_empty_text(self):
        """Test cleaning empty or whitespace-only text."""
        preprocessor = TextPreprocessor()

        assert preprocessor.clean_text("") == ""
        assert preprocessor.clean_text("   ") == ""
        assert preprocessor.clean_text("\n\t") == ""

    def test_url_removal(self):
        """Test URL removal from text."""
        preprocessor = TextPreprocessor()

        text = "Check out this link https://example.com and also www.test.org for more info"
        result = preprocessor.clean_text(text)
        # Should be lowercase and have normalized whitespace
        assert result == "check out this link and also for more info"
        assert "https://" not in result
        assert "www." not in result

    def test_emoji_removal(self):
        """Test emoji and emoticon removal."""
        preprocessor = TextPreprocessor()

        text = "I love this stock 📈😀 great news 🎉"
        result = preprocessor.clean_text(text)
        # Should be lowercase and have normalized whitespace
        assert result == "i love this stock great news"
        assert "📈" not in result
        assert "😀" not in result
        assert "🎉" not in result

    def test_case_normalization(self):
        """Test that text is converted to lowercase."""
        preprocessor = TextPreprocessor()

        text = "EQUINOR Stock Is Going UP!"
        result = preprocessor.clean_text(text)
        assert result == "equinor stock is going up"

    def test_punctuation_removal(self):
        """Test punctuation removal while preserving spaces."""
        preprocessor = TextPreprocessor()

        text = "Hello, world! How are you?"
        result = preprocessor.clean_text(text)
        assert result == "hello world how are you"

    def test_whitespace_normalization(self):
        """Test normalization of multiple whitespace characters."""
        preprocessor = TextPreprocessor()

        text = "This  has   multiple   spaces\tand\ttabs"
        result = preprocessor.clean_text(text)
        assert result == "this has multiple spaces and tabs"

    def test_slang_replacement(self):
        """Test slang term replacement."""
        slang_dict = {"aksje": "stock", "kjop": "buy"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(slang_dict, f)
            temp_path = Path(f.name)

        try:
            preprocessor = TextPreprocessor(temp_path)
            text = "Jeg vil kjop aksje i Equinor"
            result = preprocessor.clean_text(text)
            assert "stock" in result
            assert "buy" in result
            assert "aksje" not in result
            assert "kjop" not in result
        finally:
            temp_path.unlink()

    def test_comprehensive_cleaning(self):
        """Test full cleaning pipeline with realistic forum post."""
        preprocessor = TextPreprocessor()

        text = "EQUINOR aksje går opp 📈! Sjekk https://trading.com/eqnr #stocks"
        result = preprocessor.clean_text(text)

        # Should be lowercase
        assert result.islower()

        # Should not contain URLs
        assert "https://" not in result

        # Should not contain emojis
        assert "📈" not in result

        # Should not contain punctuation/hashtags
        assert "#" not in result
        assert "!" not in result

        # Should normalize whitespace
        assert "  " not in result


class TestIndividualMethods:
    """Test individual preprocessing methods."""

    def test_remove_urls(self):
        """Test URL removal method specifically."""
        preprocessor = TextPreprocessor()

        test_cases = [
            ("Visit https://example.com", "Visit "),
            ("Check www.test.org and https://another.com", "Check  and "),
            ("No URLs here", "No URLs here"),
            ("http://short.url", ""),
        ]

        for input_text, expected in test_cases:
            assert preprocessor.remove_urls(input_text) == expected

    def test_remove_emojis(self):
        """Test emoji removal method specifically."""
        preprocessor = TextPreprocessor()

        text = "Happy 😀 sad 😢 excited 🎉"
        result = preprocessor.remove_emojis(text)
        assert "😀" not in result
        assert "😢" not in result
        assert "🎉" not in result
        # Note: remove_emojis preserves spaces, doesn't normalize them
        assert "Happy  sad  excited " == result

    def test_remove_punctuation(self):
        """Test punctuation removal method specifically."""
        preprocessor = TextPreprocessor()

        text = "Hello, world! How's it going?"
        result = preprocessor.remove_punctuation(text)
        assert result == "Hello  world  How s it going "

    def test_normalize_whitespace(self):
        """Test whitespace normalization method specifically."""
        preprocessor = TextPreprocessor()

        text = "This  has   multiple\tspaces\nand\tlines"
        result = preprocessor.normalize_whitespace(text)
        assert result == "This has multiple spaces and lines"

    def test_replace_slang_no_dict(self):
        """Test slang replacement with no dictionary loaded."""
        preprocessor = TextPreprocessor()
        text = "Some random text"
        assert preprocessor.replace_slang(text) == text


class TestConvenienceFunction:
    """Test the convenience clean_text function."""

    def test_clean_text_function(self):
        """Test the standalone clean_text function."""
        text = "Test TEXT with URL https://example.com and emoji 😀"
        result = clean_text(text)

        assert result.islower()
        assert "https://" not in result
        assert "😀" not in result

    def test_clean_text_with_slang_dict(self):
        """Test clean_text function with slang dictionary."""
        slang_dict = {"test": "replacement"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(slang_dict, f)
            temp_path = Path(f.name)

        try:
            text = "This is a test"
            result = clean_text(text, temp_path)
            assert "replacement" in result
            assert "test" not in result
        finally:
            temp_path.unlink()


class TestDefaultFinanceSlang:
    """Test the default finance slang dictionary."""

    def test_default_slang_structure(self):
        """Test that default slang dictionary has expected structure."""
        assert isinstance(DEFAULT_FINANCE_SLANG, dict)
        assert len(DEFAULT_FINANCE_SLANG) > 0

        # Test some key mappings
        assert "aksje" in DEFAULT_FINANCE_SLANG
        assert "aktie" in DEFAULT_FINANCE_SLANG
        assert "eqnr" in DEFAULT_FINANCE_SLANG

        # Test that values are strings
        for key, value in DEFAULT_FINANCE_SLANG.items():
            assert isinstance(key, str)
            assert isinstance(value, str)


class TestRealWorldExamples:
    """Test with realistic forum post examples."""

    def test_norwegian_forum_post(self):
        """Test preprocessing of realistic Norwegian forum post."""
        preprocessor = TextPreprocessor()

        post = "EQUINOR aksje går til himmels 📈! Sterk kvartalsrapport på https://borsen.no/eqnr #Equinor"
        result = preprocessor.clean_text(post)

        # Check basic cleaning
        assert result.islower()
        assert "📈" not in result
        assert "https://" not in result
        assert "#" not in result

        # Check content preservation
        assert "equinor" in result
        assert "aksje" in result
        assert "går" in result
        assert "sterk" in result

    def test_swedish_forum_post(self):
        """Test preprocessing of realistic Swedish forum post."""
        preprocessor = TextPreprocessor()

        post = "VOLVO aktie stiger mycket 🎉! Bra kvartalsrapport från https://borsen.se/volvo #Volvo"
        result = preprocessor.clean_text(post)

        # Check basic cleaning
        assert result.islower()
        assert "🎉" not in result
        assert "https://" not in result
        assert "#" not in result

        # Check content preservation
        assert "volvo" in result
        assert "aktie" in result
        assert "stiger" in result
        assert "bra" in result
