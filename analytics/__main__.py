"""
CLI Interface for NSSM Analytics Module

Provides command-line access to sentiment aggregation and anomaly detection functionality.
"""

import argparse
import logging
import sys
from datetime import datetime

from .aggregator import SentimentAggregator


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def run_aggregation(args):
    """Run sentiment aggregation pipeline."""
    aggregator = SentimentAggregator()

    print(f"🚀 Starting sentiment aggregation pipeline...")
    print(f"   📅 Hours back: {args.hours_back}")
    print(f"   ⏱️  Window size: {args.window_minutes} minutes")
    print(f"   🎯 Min confidence: {args.min_confidence}")

    result = aggregator.run_aggregation_pipeline(
        hours_back=args.hours_back,
        window_minutes=args.window_minutes,
        min_confidence=args.min_confidence
    )

    if result['success']:
        print("✅ Aggregation pipeline completed successfully!")
        print(f"   📊 Posts processed: {result['posts_fetched']}")
        print(f"   📈 Aggregates computed: {result['aggregates_computed']}")
        print(f"   💾 Aggregates persisted: {result['aggregates_persisted']}")
    else:
        print(f"❌ Aggregation pipeline failed: {result['error']}")
        return 1

    return 0


def run_anomaly_detection(args):
    """Run anomaly detection pipeline."""
    aggregator = SentimentAggregator()

    print(f"🔍 Starting anomaly detection pipeline...")
    print(f"   📅 Hours back: {args.hours_back}")
    print(f"   📏 Z-score threshold: {args.zscore_threshold}")
    print(f"   📊 Min post count: {args.min_post_count}")

    result = aggregator.run_anomaly_detection_pipeline(
        hours_back=args.hours_back,
        zscore_threshold=args.zscore_threshold,
        min_post_count=args.min_post_count
    )

    if result['success']:
        print("✅ Anomaly detection pipeline completed successfully!")
        print(f"   🚨 Anomalies detected: {result['anomalies_detected']}")
        print(f"   💾 Anomalies persisted: {result['anomalies_persisted']}")
    else:
        print(f"❌ Anomaly detection pipeline failed: {result['error']}")
        return 1

    return 0


def show_status(args):
    """Show analytics status and statistics."""
    aggregator = SentimentAggregator()

    print(f"📊 NSSM Analytics Status")
    print(f"{'='*50}")

    try:
        # Get recent aggregation stats
        posts_df = aggregator.fetch_recent_posts(hours_back=args.days_back)
        if not posts_df.empty:
            print(f"\n📈 Recent Posts (last {args.days_back} days):")
            print(f"   Total posts: {len(posts_df)}")
            print(f"   Unique tickers: {posts_df['ticker'].nunique()}")
            print(f"   Date range: {posts_df['timestamp'].min()} to {posts_df['timestamp'].max()}")

            # Sentiment distribution
            sentiment_stats = posts_df['sentiment_score'].describe()
            print(f"\n🎭 Sentiment Statistics:")
            print(".3f"            print(".3f"            print(".3f"            print(".3f"
            # Top tickers by post count
            top_tickers = posts_df['ticker'].value_counts().head(5)
            print(f"\n🏆 Top Tickers by Post Count:")
            for ticker, count in top_tickers.items():
                print(f"   {ticker}: {count} posts")
        else:
            print(f"\n⚠️  No posts found in the last {args.days_back} days")

    except Exception as e:
        print(f"❌ Error retrieving status: {e}")
        return 1

    return 0


def run_combined_pipeline(args):
    """Run both aggregation and anomaly detection pipelines."""
    aggregator = SentimentAggregator()

    print(f"🚀 Starting combined analytics pipeline...")
    print(f"   📅 Hours back: {args.hours_back}")
    print(f"   ⏱️  Window size: {args.window_minutes} minutes")
    print(f"   🎯 Min confidence: {args.min_confidence}")
    print(f"   📏 Z-score threshold: {args.zscore_threshold}")

    # Step 1: Aggregation
    print(f"\n📊 Step 1: Running aggregation pipeline...")
    agg_result = aggregator.run_aggregation_pipeline(
        hours_back=args.hours_back,
        window_minutes=args.window_minutes,
        min_confidence=args.min_confidence
    )

    if not agg_result['success']:
        print(f"❌ Aggregation failed: {agg_result['error']}")
        return 1

    # Step 2: Anomaly Detection
    print(f"\n🔍 Step 2: Running anomaly detection pipeline...")
    anomaly_result = aggregator.run_anomaly_detection_pipeline(
        hours_back=args.hours_back,
        zscore_threshold=args.zscore_threshold,
        min_post_count=args.min_post_count
    )

    if not anomaly_result['success']:
        print(f"❌ Anomaly detection failed: {anomaly_result['error']}")
        return 1

    # Summary
    print(f"\n🎉 Combined pipeline completed successfully!")
    print(f"   📊 Posts processed: {agg_result['posts_fetched']}")
    print(f"   📈 Aggregates created: {agg_result['aggregates_persisted']}")
    print(f"   🚨 Anomalies detected: {anomaly_result['anomalies_persisted']}")
    print(".2f"
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="NSSM Analytics - Sentiment Aggregation and Anomaly Detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m analytics aggregate --hours-back 48
  python -m analytics anomalies --zscore-threshold 2.5
  python -m analytics pipeline --hours-back 24 --window-minutes 10
  python -m analytics status --days-back 7
        """
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Aggregate command
    agg_parser = subparsers.add_parser('aggregate', help='Run sentiment aggregation pipeline')
    agg_parser.add_argument('--hours-back', type=int, default=24, help='Hours to look back for posts')
    agg_parser.add_argument('--window-minutes', type=int, default=5, help='Aggregation window size in minutes')
    agg_parser.add_argument('--min-confidence', type=float, default=0.5, help='Minimum sentiment confidence')

    # Anomalies command
    anomaly_parser = subparsers.add_parser('anomalies', help='Run anomaly detection pipeline')
    anomaly_parser.add_argument('--hours-back', type=int, default=24, help='Hours of historical data to analyze')
    anomaly_parser.add_argument('--zscore-threshold', type=float, default=2.0, help='Minimum z-score for anomaly detection')
    anomaly_parser.add_argument('--min-post-count', type=int, default=5, help='Minimum posts to consider for analysis')

    # Pipeline command (combined)
    pipeline_parser = subparsers.add_parser('pipeline', help='Run complete analytics pipeline')
    pipeline_parser.add_argument('--hours-back', type=int, default=24, help='Hours to look back for posts')
    pipeline_parser.add_argument('--window-minutes', type=int, default=5, help='Aggregation window size in minutes')
    pipeline_parser.add_argument('--min-confidence', type=float, default=0.5, help='Minimum sentiment confidence')
    pipeline_parser.add_argument('--zscore-threshold', type=float, default=2.0, help='Minimum z-score for anomaly detection')
    pipeline_parser.add_argument('--min-post-count', type=int, default=5, help='Minimum posts to consider for analysis')

    # Status command
    status_parser = subparsers.add_parser('status', help='Show analytics status and statistics')
    status_parser.add_argument('--days-back', type=int, default=7, help='Days to look back for status')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Setup logging
    setup_logging(args.verbose)

    # Execute command
    if args.command == 'aggregate':
        return run_aggregation(args)
    elif args.command == 'anomalies':
        return run_anomaly_detection(args)
    elif args.command == 'pipeline':
        return run_combined_pipeline(args)
    elif args.command == 'status':
        return show_status(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
