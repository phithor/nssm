"""
Text Preprocessing Utilities for NLP Sentiment Analysis

Provides comprehensive text cleaning and normalization for Norwegian and Swedish
forum posts before sentiment analysis.
"""

import json
import re
from pathlib import Path
from typing import Dict, Optional


class TextPreprocessor:
    """Text preprocessing pipeline for forum posts."""

    def __init__(self, slang_dict_path: Optional[Path] = None):
        """
        Initialize the preprocessor with optional slang dictionary.

        Args:
            slang_dict_path: Path to JSON file containing slang mappings
        """
        self.slang_dict = self._load_slang_dict(slang_dict_path)

        # Compile regex patterns for efficiency
        self.url_pattern = re.compile(r"https?://\S+|www\.\S+")
        self.emoji_pattern = re.compile(
            r"[\U0001F600-\U0001F64F]|[\U0001F300-\U0001F5FF]|[\U0001F680-\U0001F6FF]|"
            r"[\U0001F1E0-\U0001F1FF]|[\U00002500-\U00002BEF]|[\U00002702-\U000027B0]|"
            r"[\U000024C2-\U0001F251]|[\U0001f926-\U0001f937]|[\U00010000-\U0010ffff]|"
            r"[\u2640-\u2642]|[\u2600-\u2B55]|[\u200d]|[\u23cf]|[\u23e9]|[\u231a]"
        )
        self.punctuation_pattern = re.compile(r"[^\w\s]")
        self.extra_whitespace_pattern = re.compile(r"\s+")

    def _load_slang_dict(self, path: Optional[Path]) -> Dict[str, str]:
        """Load slang dictionary from JSON file."""
        if path and path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load slang dictionary from {path}: {e}")
                return {}
        return {}

    def clean_text(self, text: str) -> str:
        """
        Comprehensive text cleaning pipeline.

        Args:
            text: Raw text to clean

        Returns:
            Cleaned and normalized text
        """
        if not text or not text.strip():
            return ""

        # Step 1: Remove URLs
        text = self.remove_urls(text)

        # Step 2: Remove emojis
        text = self.remove_emojis(text)

        # Step 3: Convert to lowercase
        text = text.lower()

        # Step 4: Replace slang terms
        text = self.replace_slang(text)

        # Step 5: Remove punctuation (but keep spaces and word chars)
        text = self.remove_punctuation(text)

        # Step 6: Normalize whitespace
        text = self.normalize_whitespace(text)

        # Step 7: Strip leading/trailing whitespace
        return text.strip()

    def remove_urls(self, text: str) -> str:
        """Remove URLs from text."""
        return self.url_pattern.sub("", text)

    def remove_emojis(self, text: str) -> str:
        """Remove emojis and emoticons from text."""
        return self.emoji_pattern.sub("", text)

    def remove_punctuation(self, text: str) -> str:
        """Remove punctuation while preserving spaces and word characters."""
        return self.punctuation_pattern.sub(" ", text)

    def normalize_whitespace(self, text: str) -> str:
        """Normalize multiple whitespace characters to single spaces."""
        return self.extra_whitespace_pattern.sub(" ", text)

    def replace_slang(self, text: str) -> str:
        """
        Replace slang terms with canonical forms using the loaded dictionary.

        Args:
            text: Text to process

        Returns:
            Text with slang terms replaced
        """
        if not self.slang_dict:
            return text

        words = text.split()
        processed_words = []

        for word in words:
            # Check for exact matches first
            if word in self.slang_dict:
                processed_words.append(self.slang_dict[word])
            else:
                processed_words.append(word)

        return " ".join(processed_words)


# Convenience function for quick preprocessing
def clean_text(text: str, slang_dict_path: Optional[Path] = None) -> str:
    """
    Convenience function for text preprocessing.

    Args:
        text: Raw text to clean
        slang_dict_path: Optional path to slang dictionary JSON file

    Returns:
        Cleaned text
    """
    preprocessor = TextPreprocessor(slang_dict_path)
    return preprocessor.clean_text(text)


# Default finance slang dictionary for Scandinavian markets
DEFAULT_FINANCE_SLANG = {
    # Norwegian slang
    "aksje": "stock",
    "aksjer": "stocks",
    "børs": "exchange",
    "kurs": "price",
    "selg": "sell",
    "kjop": "buy",
    "kjope": "buy",
    "stigning": "rise",
    "fall": "fall",
    "profit": "profit",
    "tap": "loss",
    "investering": "investment",
    "portefølje": "portfolio",
    # Swedish slang
    "aktie": "stock",
    "aktier": "stocks",
    "börsen": "exchange",
    "kurs": "price",
    "sälj": "sell",
    "köp": "buy",
    "köpa": "buy",
    "uppgång": "rise",
    "nedgång": "fall",
    "vinst": "profit",
    "förlust": "loss",
    "investering": "investment",
    "portfölj": "portfolio",
    # Common abbreviations
    "eqnr": "equinor",
    "dnb": "dnb_bank",
    "nhy": "norsk_hydro",
    "tel": "telenor",
    "yara": "yara_international",
    "aker": "aker_solutions",
}
