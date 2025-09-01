"""
Lightweight Language Detection for Norwegian and Swedish Text

Provides a simple, fast heuristic to determine whether forum posts are
written in Norwegian (Bokmål/Nynorsk) or Swedish based on locale hints
and character-level patterns.
"""

import re
from collections import Counter
from typing import Optional


def detect_lang(text: str, locale_hint: Optional[str] = None) -> str:
    """
    Detect language of text using locale hint and character pattern analysis.

    Args:
        text: The text content to analyze
        locale_hint: Optional hint from forum locale ('no' or 'sv')

    Returns:
        'no' for Norwegian or 'sv' for Swedish

    The function first checks the locale_hint, then falls back to character
    bigram frequency analysis to distinguish between Norwegian and Swedish.
    """
    if not text or not text.strip():
        return "no"  # Default fallback

    # Step 1: Use locale hint if available and valid
    if locale_hint in ("no", "sv"):
        return locale_hint

    # Step 2: Character-level analysis
    return _analyze_character_patterns(text)


def _analyze_character_patterns(text: str) -> str:
    """
    Analyze character patterns to distinguish Norwegian from Swedish.

    Uses bigram frequency analysis focusing on letters that differ between
    the two languages (æ/ø in Norwegian vs ä/ö in Swedish).
    """
    # Normalize text for analysis
    text = text.lower()

    # Count relevant character bigrams
    norwegian_chars = ["æ", "ø", "å"]
    swedish_chars = ["ä", "ö", "å"]

    norwegian_count = sum(text.count(char) for char in norwegian_chars)
    swedish_count = sum(text.count(char) for char in swedish_chars)

    # Additional heuristics based on common patterns
    # Swedish tends to use more 'ä' and 'ö', Norwegian uses more 'æ' and 'ø'
    if norwegian_count > swedish_count:
        return "no"
    elif swedish_count > norwegian_count:
        return "sv"

    # Tiebreaker: look for language-specific word patterns
    norwegian_words = [
        "jeg",
        "det",
        "som",
        "på",
        "er",
        "en",
        "og",
        "den",
        "til",
        "av",
        "går",
        "for",
        "med",
        "fra",
        "kan",
        "vil",
        "bli",
        "har",
        "hadde",
    ]
    swedish_words = [
        "jag",
        "det",
        "som",
        "på",
        "är",
        "en",
        "och",
        "den",
        "till",
        "av",
        "går",
        "för",
        "med",
        "från",
        "kan",
        "vill",
        "bli",
        "har",
        "hade",
        "upp",
        "imorgon",
        "tycker",
        "vad",
        "ni",
    ]

    # Split text into words and count matches
    words = text.lower().split()
    norwegian_word_count = sum(1 for word in words if word in norwegian_words)
    swedish_word_count = sum(1 for word in words if word in swedish_words)

    if norwegian_word_count > swedish_word_count:
        return "no"
    elif swedish_word_count > norwegian_word_count:
        return "sv"

    # Final fallback to Norwegian (more common in the context)
    return "no"
