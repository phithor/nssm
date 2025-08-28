"""
CLI Entry Point for Forum Scrapers

Provides the 'python -m scraper run' command with scheduling,
logging configuration, and graceful shutdown handling.
"""

import argparse
import logging
import logging.config
import signal
import sys
import time
from typing import Any, Dict

import schedule

from .persistence import ScraperPersistence


def setup_logging(verbose: bool = False) -> None:
    """
    Configure logging for the scraper application.

    Args:
        verbose: Enable verbose logging if True
    """
    log_level = "DEBUG" if verbose else "INFO"

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": (
                    "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "detailed" if verbose else "standard",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.FileHandler",
                "level": "INFO",
                "formatter": "detailed",
                "filename": "scraper.log",
                "mode": "a",
            },
        },
        "loggers": {
            "": {
                "handlers": ["console", "file"],
                "level": log_level,
                "propagate": False,
            },
            "scraper": {
                "handlers": ["console", "file"],
                "level": log_level,
                "propagate": False,
            },
            "db": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(logging_config)


def run_scraping_job(max_pages: int = 5) -> Dict[str, Any]:
    """
    Run the main scraping job for all forums.

    Args:
        max_pages: Maximum number of pages to scrape per forum

    Returns:
        Dictionary with scraping results
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting forum scraping job")

    try:
        with ScraperPersistence() as persistence:
            results = persistence.scrape_all_forums(max_pages)

            # Log results
            logger.info(f"Scraping job completed: {results}")

            # Show current post counts
            counts = persistence.get_post_count_by_forum()
            if counts:
                logger.info("Current post counts by forum:")
                for forum_name, count in counts.items():
                    logger.info(f"  {forum_name}: {count} posts")

            return results

    except Exception as e:
        logger.error(f"Error during scraping job: {e}")
        return {"error": str(e)}


def schedule_scraping(interval_minutes: int = 1, max_pages: int = 5) -> None:
    """
    Schedule scraping jobs to run at regular intervals.

    Args:
        interval_minutes: Interval between scraping jobs in minutes
        max_pages: Maximum number of pages to scrape per forum
    """
    logger = logging.getLogger(__name__)

    # Schedule the job
    schedule.every(interval_minutes).minutes.do(run_scraping_job, max_pages)

    logger.info(f"Scheduled scraping job to run every {interval_minutes} minute(s)")
    logger.info(f"Maximum pages per forum: {max_pages}")

    # Run initial job immediately
    logger.info("Running initial scraping job...")
    run_scraping_job(max_pages)

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down gracefully...")
    except Exception as e:
        logger.error(f"Unexpected error in scheduling loop: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger = logging.getLogger(__name__)
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="NSSM Forum Scraper - Scrape Nordic investor forums",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m scraper run                    # Run scraper every minute
  python -m scraper run --interval 5       # Run every 5 minutes
  python -m scraper run --max-pages 10     # Scrape up to 10 pages per forum
  python -m scraper run --verbose          # Enable verbose logging
  python -m scraper run --once             # Run once and exit
        """,
    )

    parser.add_argument("command", choices=["run"], help="Command to execute")

    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=1,
        help="Interval between scraping jobs in minutes (default: 1)",
    )

    parser.add_argument(
        "--max-pages",
        "-p",
        type=int,
        default=5,
        help="Maximum number of pages to scrape per forum (default: 5)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Run scraping job once and exit (don't schedule)",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        if args.command == "run":
            if args.once:
                logger.info("Running scraping job once...")
                results = run_scraping_job(args.max_pages)
                logger.info(f"Job completed: {results}")
            else:
                logger.info("Starting scheduled scraping service...")
                schedule_scraping(args.interval, args.max_pages)
        else:
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
