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
    run_parser.add_argument(
        "--loop",
        action="store_true",
        help="Run continuously, checking for new posts periodically"
    )
    run_parser.add_argument(
        "--loop-interval",
        type=int,
        default=300,
        help="Interval between processing cycles in seconds (default: 300)"
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

    print("Configuration:")
    print(f"  Limit: {args.limit} posts per cycle")
    print(f"  Batch size: {args.batch_size}")
    print(f"  Language hint: {args.language_hint or 'auto'}")
    print(f"  Forum IDs: {args.forum_ids or 'all'}")
    print(f"  Dry run: {args.dry_run}")
    print(f"  Verbose: {args.verbose}")
    print(f"  Continuous mode: {args.loop}")
    if args.loop:
        print(f"  Loop interval: {args.loop_interval} seconds")
    print()

    if args.dry_run:
        print("🔍 DRY RUN MODE - No actual analysis will be performed")
        return

    try:
        import os
        import time
        from datetime import datetime
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from .db_io import SentimentDBHandler
        from .infer import analyze_sentiment
        
        # Get database URL
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            print("❌ DATABASE_URL environment variable not set")
            return
            
        # Create database connection
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(bind=engine)
        
        print("📊 Starting sentiment analysis...")
        
        # Initialize handler
        handler = SentimentDBHandler(SessionLocal)
        
        def process_posts():
            """Process one batch of posts."""
            # Fetch unscored posts
            posts = handler.fetch_unscored_posts(
                limit=args.limit,
                language_hint=args.language_hint,
                forum_ids=args.forum_ids
            )
            
            if not posts:
                if args.verbose:
                    print(f"[{datetime.now()}] ✅ No posts need sentiment analysis")
                return 0, 0, 0
                
            print(f"[{datetime.now()}] 📝 Found {len(posts)} posts to analyze")
            
            # Process in batches
            total_processed = 0
            total_success = 0
            total_errors = 0
            
            for i in range(0, len(posts), args.batch_size):
                batch = posts[i:i + args.batch_size]
                batch_num = (i // args.batch_size) + 1
                total_batches = (len(posts) + args.batch_size - 1) // args.batch_size
                
                if args.verbose:
                    print(f"⚙️  Processing batch {batch_num}/{total_batches} ({len(batch)} posts)...")
                
                try:
                    # Run sentiment analysis on batch
                    batch_result = analyze_sentiment(
                        posts=batch,
                        locale_hint=args.language_hint,
                        batch_size=len(batch)
                    )
                    
                    # Save results
                    success_count, error_count = handler.save_batch_results(batch_result)
                    
                    total_processed += len(batch)
                    total_success += success_count
                    total_errors += error_count
                    
                    if args.verbose:
                        print(f"  ✅ Batch {batch_num}: {success_count} saved, {error_count} errors")
                        
                except Exception as e:
                    print(f"  ❌ Batch {batch_num} failed: {e}")
                    total_errors += len(batch)
                    continue
            
            return total_processed, total_success, total_errors
        
        if args.loop:
            print("🔄 Running in continuous mode. Press Ctrl+C to stop.")
            cycle_count = 0
            grand_total_processed = 0
            grand_total_success = 0
            grand_total_errors = 0
            
            try:
                while True:
                    cycle_count += 1
                    print(f"\n🔄 Processing cycle {cycle_count}")
                    
                    processed, success, errors = process_posts()
                    grand_total_processed += processed
                    grand_total_success += success
                    grand_total_errors += errors
                    
                    if processed > 0:
                        print(f"✅ Cycle {cycle_count}: {processed} processed, {success} analyzed, {errors} errors")
                    
                    if args.verbose or processed == 0:
                        print(f"💤 Waiting {args.loop_interval} seconds until next cycle...")
                        
                    time.sleep(args.loop_interval)
                    
            except KeyboardInterrupt:
                print(f"\n🛑 Stopped after {cycle_count} cycles")
                print(f"📊 Total across all cycles: {grand_total_processed} processed, {grand_total_success} analyzed, {grand_total_errors} errors")
                
        else:
            # Single run mode
            processed, success, errors = process_posts()
            
            print()
            print("📈 Analysis Complete:")
            print(f"  Total posts processed: {processed}")
            print(f"  Successfully analyzed: {success}")
            print(f"  Errors: {errors}")
            
            if success > 0 and processed > 0:
                success_rate = (success / processed) * 100
                print(f"  Success rate: {success_rate:.1f}%")
            
    except Exception as e:
        print(f"❌ Sentiment analysis failed: {e}")
        import traceback
        if args.verbose:
            traceback.print_exc()


def show_sentiment_status(args):
    """Show sentiment analysis status and statistics."""
    print("=== NSSM Sentiment Analysis Status ===")
    print()

    print("Configuration:")
    print(f"  Days back: {args.days_back}")
    print(f"  Forum IDs: {args.forum_ids or 'all'}")
    print()

    try:
        import os
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from .db_io import SentimentDBHandler
        
        # Get database URL
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            print("❌ DATABASE_URL environment variable not set")
            return
            
        # Create database connection
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(bind=engine)
        
        # Initialize handler
        handler = SentimentDBHandler(SessionLocal)
        
        # Get statistics
        stats = handler.get_sentiment_stats(
            days_back=args.days_back,
            forum_ids=args.forum_ids
        )
        
        if not stats:
            print("❌ Could not retrieve statistics")
            return
            
        print("📊 Analysis Statistics:")
        print(f"  Total posts ({args.days_back} days): {stats.get('total_posts', 0):,}")
        print(f"  Analyzed posts: {stats.get('analyzed_posts', 0):,}")
        print(f"  Posts needing analysis: {stats.get('unanalyzed_posts', 0):,}")
        
        coverage = stats.get('analysis_coverage', 0.0)
        print(f"  Coverage: {coverage * 100:.1f}%")
        
        if stats.get('avg_sentiment') is not None:
            avg_sentiment = stats['avg_sentiment']
            print(f"  Average sentiment: {avg_sentiment:.3f}")
            print(f"  Sentiment range: {stats.get('min_sentiment', 0):.3f} to {stats.get('max_sentiment', 0):.3f}")
            
            # Sentiment interpretation
            if avg_sentiment > 0.1:
                print("  📈 Overall sentiment: Positive")
            elif avg_sentiment < -0.1:
                print("  📉 Overall sentiment: Negative") 
            else:
                print("  📊 Overall sentiment: Neutral")
        else:
            print("  📊 No sentiment data available yet")
            
        # Get posts needing analysis
        pending_count = handler.get_posts_needing_analysis()
        if pending_count > 0:
            print(f"  ⏳ {pending_count:,} posts ready for analysis (>1 hour old)")
            
    except Exception as e:
        print(f"❌ Status check failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
