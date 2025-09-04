"""
Unit tests for NLP language detection module.
"""

from nlp.lang_detect import _analyze_character_patterns, detect_lang


class TestDetectLang:
    """Test cases for the main detect_lang function."""

    def test_empty_text(self):
        """Test handling of empty or whitespace-only text."""
        assert detect_lang("") == "en"
        assert detect_lang("   ") == "en"
        assert detect_lang("\n\t") == "en"

    def test_locale_hint_priority(self):
        """Test that locale_hint takes precedence over text analysis."""
        # Norwegian hint should override Swedish text
        text_with_swedish = "Jag älskar programmering"
        assert detect_lang(text_with_swedish, locale_hint="no") == "no"

        # Swedish hint should override Norwegian text
        text_with_norwegian = "Jeg elsker programmering"
        assert detect_lang(text_with_norwegian, locale_hint="sv") == "sv"

        # English hint should override any text
        text_with_norwegian = "Jeg elsker programmering"
        assert detect_lang(text_with_norwegian, locale_hint="en") == "en"

    def test_invalid_locale_hint(self):
        """Test that invalid locale hints are ignored."""
        text_with_norwegian = "Jeg elsker programmering"
        assert detect_lang(text_with_norwegian, locale_hint="invalid") == "no"

    def test_english_detection(self):
        """Test detection of English text."""
        english_texts = [
            "I love programming",
            "This is a great day",
            "What are you doing today?",
            "The quick brown fox jumps over the lazy dog",
            "I am going to the store to buy milk",
            "Hello world, how are you?",
            "The weather is nice today",
        ]

        for text in english_texts:
            assert detect_lang(text) == "en", f"Failed to detect English: {text}"

    def test_norwegian_detection(self):
        """Test detection of Norwegian text."""
        norwegian_texts = [
            "Jeg elsker programmering",
            "Det er en fin dag",
            "Hva gjør du i dag?",
            "æøåÆØÅ",  # Norwegian special characters
            "Jeg går på butikken for å kjøpe melk",
        ]

        for text in norwegian_texts:
            assert detect_lang(text) == "no", f"Failed to detect Norwegian: {text}"

    def test_swedish_detection(self):
        """Test detection of Swedish text."""
        swedish_texts = [
            "Jag älskar programmering",
            "Det är en fin dag",
            "Vad gör du idag?",
            "äöåÄÖÅ",  # Swedish special characters
            "Jag går till affären för att köpa mjölk",
        ]

        for text in swedish_texts:
            assert detect_lang(text) == "sv", f"Failed to detect Swedish: {text}"

    def test_mixed_scandinavian_text(self):
        """Test detection with text that could be either language."""
        mixed_texts = [
            "Det er bra",  # Could be both
            "På en dag",  # Could be both
            "Som alltid",  # Could be both
        ]

        # These should default to Norwegian (our fallback)
        for text in mixed_texts:
            assert detect_lang(text) == "no", f"Failed on mixed text: {text}"

    def test_case_insensitive(self):
        """Test that detection is case insensitive."""
        assert detect_lang("JEG ELSKER PROGRAMMERING") == "no"
        assert detect_lang("jag älskar programmering") == "sv"
        assert detect_lang("JeG eLsKeR PrOgRaMmErInG") == "no"


class TestAnalyzeCharacterPatterns:
    """Test cases for the internal character pattern analysis."""

    def test_norwegian_special_chars(self):
        """Test detection based on Norwegian special characters."""
        assert _analyze_character_patterns("æøå") == "no"
        assert _analyze_character_patterns("ÆØÅ") == "no"
        assert _analyze_character_patterns("Jeg bruker æøå") == "no"

    def test_swedish_special_chars(self):
        """Test detection based on Swedish special characters."""
        assert _analyze_character_patterns("äöå") == "sv"
        assert _analyze_character_patterns("ÄÖÅ") == "sv"
        assert _analyze_character_patterns("Jag använder äöå") == "sv"

    def test_mixed_characters(self):
        """Test with mixed Norwegian and Swedish characters."""
        # More Norwegian characters should win
        assert _analyze_character_patterns("æøä") == "no"  # æø=2 NO, ä=1 SE
        assert _analyze_character_patterns("æøå") == "no"  # æøå=3 NO, no SE

        # More Swedish characters should win
        assert _analyze_character_patterns("äöæ") == "sv"  # äö=2 SE, æ=1 NO
        assert _analyze_character_patterns("æäö") == "sv"  # æ=1 NO, äö=2 SE
        assert _analyze_character_patterns("äøæ") == "no"  # ä=1 SE, øæ=2 NO

    def test_equal_characters(self):
        """Test fallback when character counts are equal."""
        # Equal counts should fall back to word-based detection, then to Norwegian
        assert _analyze_character_patterns("æä") == "no"
        assert _analyze_character_patterns("øö") == "no"

    def test_no_special_chars(self):
        """Test text without special Scandinavian characters."""
        # Should fall back to word-based detection
        assert _analyze_character_patterns("Hello world") == "no"
        assert _analyze_character_patterns("Programming is fun") == "no"


class TestRealWorldExamples:
    """Test with more realistic forum post examples."""

    def test_norwegian_forum_posts(self):
        """Test with realistic Norwegian forum posts."""
        posts = [
            "Tror Equinor går opp i morgen, hva synes dere?",
            "Elsker når aksjemarkedet stiger! 📈",
            "Hva er deres favoritt aksje for øyeblikket?",
            "Markedet ser sterkt ut nå, kjøp på dip?",
        ]

        for post in posts:
            result = detect_lang(post)
            assert result == "no", f"Failed Norwegian post: {post}"

    def test_swedish_forum_posts(self):
        """Test with realistic Swedish forum posts."""
        posts = [
            "Tror Equinor går upp imorgon, vad tycker ni?",
            "Älskar när aktiemarknaden stiger! 📈",
            "Vad är er favoritaktie för tillfället?",
            "Marknaden ser stark ut nu, köp på dip?",
        ]

        for post in posts:
            result = detect_lang(post)
            assert result == "sv", f"Failed Swedish post: {post}"
