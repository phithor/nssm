"""
Command-line interface for NLP preprocessing utilities.

Usage:
    python -m nlp preprocess "Your text here"
    python -m nlp test-lang "Sample text"
"""

import argparse

# Configure logging
import logging
import sys
from pathlib import Path

from .db_io import get_sentiment_statistics, get_unscored_posts, save_sentiment_scores
from .infer import analyze_sentiment
from .lang_detect import detect_lang
from .model import get_model_info, preload_models
from .preprocess import DEFAULT_FINANCE_SLANG, clean_text

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="NSSM NLP Utilities - Text Preprocessing and Language Detection"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Preprocess command
    preprocess_parser = subparsers.add_parser(
        "preprocess", help="Clean and preprocess text for sentiment analysis"
    )
    preprocess_parser.add_argument("text", help="Text to preprocess")
    preprocess_parser.add_argument(
        "--slang-dict", type=Path, help="Path to custom slang dictionary JSON file"
    )
    preprocess_parser.add_argument(
        "--show-steps",
        action="store_true",
        help="Show intermediate preprocessing steps",
    )

    # Language detection command
    lang_parser = subparsers.add_parser(
        "detect-lang", help="Detect language of text (Norwegian/Swedish)"
    )
    lang_parser.add_argument("text", help="Text to analyze")
    lang_parser.add_argument(
        "--locale-hint", choices=["no", "sv"], help="Locale hint to guide detection"
    )

    # Test command
    test_parser = subparsers.add_parser(
        "test", help="Run preprocessing pipeline on sample texts"
    )

    # Model info command
    model_parser = subparsers.add_parser(
        "model-info", help="Show information about available models and cache status"
    )

    # Run sentiment analysis command
    run_parser = subparsers.add_parser(
        "run", help="Run sentiment analysis on unscored posts"
    )
    run_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of posts to process (default: 100)",
    )
    run_parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Number of posts to process simultaneously (default: 16)",
    )
    run_parser.add_argument(
        "--language-hint",
        choices=["no", "sv"],
        help="Language hint to guide analysis ('no' or 'sv')",
    )
    run_parser.add_argument(
        "--forum-ids",
        type=lambda x: [int(i) for i in x.split(",")],
        help="Comma-separated list of forum IDs to process",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without actually running analysis",
    )
    run_parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose output"
    )

    # Status command
    status_parser = subparsers.add_parser(
        "status", help="Show sentiment analysis status and statistics"
    )
    status_parser.add_argument(
        "--days-back",
        type=int,
        default=7,
        help="Number of days to look back for statistics (default: 7)",
    )
    status_parser.add_argument(
        "--forum-ids",
        type=lambda x: [int(i) for i in x.split(",")],
        help="Comma-separated list of forum IDs to filter statistics",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "preprocess":
        result = clean_text(args.text, args.slang_dict)

        if args.show_steps:
            print("=== Text Preprocessing Steps ===")
            print(f"Original: {args.text}")
            print(f"Cleaned:  {result}")
            print()

            # Show what changed
            changes = []
            if args.text != args.text.lower():
                changes.append("Case normalization")
            if any(char in args.text for char in ["æ", "ø", "å", "ä", "ö"]):
                changes.append("Special character handling")
            if any(emoji in args.text for emoji in ["📈", "😀", "🎉", "😢"]):
                changes.append("Emoji removal")
            if "http" in args.text or "www." in args.text:
                changes.append("URL removal")
            if any(punct in args.text for punct in ["!", "?", "#", "@"]):
                changes.append("Punctuation removal")
            if "  " in args.text or "\t" in args.text or "\n" in args.text:
                changes.append("Whitespace normalization")

            if changes:
                print("Applied transformations:")
                for change in changes:
                    print(f"  • {change}")
            else:
                print("No transformations applied")

        else:
            print(result)

    elif args.command == "detect-lang":
        lang = detect_lang(args.text, args.locale_hint)
        confidence_indicators = []

        # Simple confidence estimation
        if any(char in args.text.lower() for char in ["æ", "ø"]):
            confidence_indicators.append("Strong Norwegian indicators (æ/ø)")
        elif any(char in args.text.lower() for char in ["ä", "ö"]):
            confidence_indicators.append("Strong Swedish indicators (ä/ö)")

        norwegian_words = ["jeg", "det", "er", "på", "som", "en"]
        swedish_words = ["jag", "det", "är", "på", "som", "en"]
        text_words = args.text.lower().split()

        no_word_matches = sum(1 for word in text_words if word in norwegian_words)
        sv_word_matches = sum(1 for word in text_words if word in swedish_words)

        if no_word_matches > sv_word_matches:
            confidence_indicators.append(f"Norwegian word matches: {no_word_matches}")
        elif sv_word_matches > no_word_matches:
            confidence_indicators.append(f"Swedish word matches: {sv_word_matches}")

        print(f"Detected Language: {lang.upper()}")
        if args.locale_hint:
            print(f"Locale Hint: {args.locale_hint.upper()}")
        if confidence_indicators:
            print("Detection Indicators:")
            for indicator in confidence_indicators:
                print(f"  • {indicator}")

    elif args.command == "run":
        run_sentiment_analysis(args)

    elif args.command == "status":
        show_sentiment_status(args)

    elif args.command == "test":
        print("=== NSSM NLP Preprocessing Test ===")
        print()

        # Test texts in both languages
        test_texts = [
            (
                "Norwegian",
                "EQUINOR aksje går opp 📈! Sjekk https://borsen.no/eqnr #Equinor",
            ),
            (
                "Swedish",
                "VOLVO aktie stiger mycket 🎉! Bra kvartalsrapport från https://borsen.se/volvo #Volvo",
            ),
            ("Mixed", "Jeg elsker när aktier stiger! 📈😀"),
        ]

        for lang, text in test_texts:
            print(f"{lang} Text:")
            print(f"  Original: {text}")

            # Language detection
            detected_lang = detect_lang(text)
            print(f"  Detected: {detected_lang.upper()}")

            # Preprocessing
            cleaned = clean_text(text)
            print(f"  Cleaned:  {cleaned}")
            print()

    elif args.command == "model-info":
        print("=== NSSM NLP Model Information ===")
        print()

        info = get_model_info()

        print("Supported Languages:")
        for lang in info["supported_languages"]:
            config = info["model_configs"][lang]
            print(f"  {lang.upper()}: {config['model_name']} ({config['description']})")
        print()

        print("Cache Information:")
        print(f"  Cache Directory: {info['cache_directory']}")
        print(f"  Device: {info['device']}")
        print(f"  CUDA Available: {info['cuda_available']}")
        print(f"  MPS Available: {info['mps_available']}")
        print(
            f"  Cached Languages: {', '.join(info['cached_languages']) if info['cached_languages'] else 'None'}"
        )
        print()

        if not info["cached_languages"]:
            print(
                "💡 Tip: No models cached yet. Use 'preload-models' to download models for faster startup."
            )
        else:
            print(f"✅ {len(info['cached_languages'])} model(s) ready for inference!")


def run_sentiment_analysis(args):
    """Run sentiment analysis on unscored posts."""
    print("=== NSSM Sentiment Analysis ===")
    print()

    # This is a placeholder implementation
    # In a real implementation, this would:
    # 1. Get a database session factory
    # 2. Fetch unscored posts
    # 3. Run sentiment analysis
    # 4. Save results

    print("Configuration:")
    print(f"  Limit: {args.limit} posts")
    print(f"  Batch size: {args.batch_size}")
    print(f"  Language hint: {args.language_hint or 'auto'}")
    print(f"  Forum IDs: {args.forum_ids or 'all'}")
    print(f"  Dry run: {args.dry_run}")
    print(f"  Verbose: {args.verbose}")
    print()

    if args.dry_run:
        print("🔍 DRY RUN MODE - No actual analysis will be performed")
        print()

    print("📊 This command would:")
    print("  1. Connect to the database")
    print("  2. Fetch posts needing sentiment analysis")
    print("  3. Load appropriate language models")
    print("  4. Run batch sentiment analysis")
    print("  5. Save results with confidence scores")
    print()

    print("💡 To run actual sentiment analysis:")
    print("  - Ensure database is running and accessible")
    print("  - Make sure you have database credentials configured")
    print("  - Remove --dry-run flag")
    print()

    if args.verbose:
        print("🔧 Technical details:")
        print("  - Models will be loaded on-demand")
        print("  - Posts are processed in batches for efficiency")
        print("  - Results are saved atomically")
        print("  - Errors are logged but don't stop processing")


def show_sentiment_status(args):
    """Show sentiment analysis status and statistics."""
    print("=== NSSM Sentiment Analysis Status ===")
    print()

    # This is a placeholder implementation
    # In a real implementation, this would:
    # 1. Connect to database
    # 2. Get sentiment statistics
    # 3. Show coverage and performance metrics

    print("Configuration:")
    print(f"  Days back: {args.days_back}")
    print(f"  Forum IDs: {args.forum_ids or 'all'}")
    print()

    print("📊 This command would show:")
    print("  - Total posts in the period")
    print("  - Number of analyzed posts")
    print("  - Analysis coverage percentage")
    print("  - Average sentiment scores")
    print("  - Posts still needing analysis")
    print()

    print("💡 To see actual statistics:")
    print("  - Ensure database is running and accessible")
    print("  - Make sure sentiment analysis has been run")
    print()

    print("📈 Sample output format:")
    print("  Total posts (7 days): 1,247")
    print("  Analyzed posts: 892")
    print("  Coverage: 71.5%")
    print("  Average sentiment: 0.34")
    print("  Posts needing analysis: 355")


if __name__ == "__main__":
    main()
