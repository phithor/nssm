"""
NSSM Market Data Scheduler

Runs market price data fetching on an hourly schedule.
Designed to run as a background service for continuous market data ingestion.
"""

import asyncio
import logging
import signal
import sys
import time
from datetime import datetime, timedelta
from typing import List, Optional

import schedule

from db import get_database_url

from .data import OpenBBYahooFinancePriceFetcher, fetch_market_prices


class MarketDataScheduler:
    """Scheduler for running market data fetching at regular intervals."""

    def __init__(self, db_url: Optional[str] = None, fallback_to_mock: bool = False):
        self.db_url = db_url or get_database_url()
        self.fallback_to_mock = fallback_to_mock
        self.running = False
        self.logger = logging.getLogger(__name__)

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Track last successful run
        self.last_price_fetch = None

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    async def run_hourly_price_fetch(
        self, days_back: int = 1, force_refresh: bool = False
    ):
        """Fetch market price data for all tickers."""
        try:
            self.logger.info("📈 Starting scheduled price data fetch...")

            start_time = datetime.now()

            # Fetch price data for all tickers
            results = fetch_market_prices(
                db_url=self.db_url,
                days_back=days_back,
                force_refresh=force_refresh,
                fallback_to_mock=self.fallback_to_mock,
            )

            total_stored = sum(results.values())
            successful_tickers = sum(1 for count in results.values() if count > 0)

            duration = datetime.now() - start_time

            if total_stored > 0:
                self.logger.info(
                    f"✅ Price fetch completed: {total_stored} data points stored "
                    f"for {successful_tickers}/{len(results)} tickers in {duration.total_seconds():.1f}s"
                )
                self.last_price_fetch = datetime.now()
            else:
                self.logger.warning(
                    "⚠️  Price fetch completed but no new data was stored"
                )

            # Log results for each ticker
            for ticker, count in results.items():
                if count > 0:
                    self.logger.debug(f"   {ticker}: {count} data points")
                elif count == 0:
                    self.logger.debug(f"   {ticker}: no new data")

        except Exception as e:
            self.logger.error(f"💥 Scheduled price fetch failed: {e}")
            import traceback

            self.logger.debug(f"Full traceback: {traceback.format_exc()}")

    def run_hourly_price_fetch_sync(
        self, days_back: int = 1, force_refresh: bool = False
    ):
        """Synchronous wrapper for the async price fetch function."""
        try:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            loop.run_until_complete(
                self.run_hourly_price_fetch(days_back, force_refresh)
            )
            loop.close()
        except Exception as e:
            self.logger.error(f"Error in sync wrapper: {e}")

    async def run_daily_maintenance(self):
        """Run daily maintenance tasks for market data."""
        try:
            self.logger.info("🧹 Starting daily market data maintenance...")

            # Tasks that could be added:
            # - Clean up old price data beyond retention period
            # - Validate data integrity
            # - Update market configuration
            # - Performance monitoring

            self.logger.info("✅ Daily market data maintenance completed")

        except Exception as e:
            self.logger.error(f"💥 Daily maintenance failed: {e}")

    def run_daily_maintenance_sync(self):
        """Synchronous wrapper for daily maintenance."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.run_daily_maintenance())
            loop.close()
        except Exception as e:
            self.logger.error(f"Error in maintenance sync wrapper: {e}")

    def get_status(self) -> dict:
        """Get current scheduler status."""
        return {
            "running": self.running,
            "last_price_fetch": (
                self.last_price_fetch.isoformat() if self.last_price_fetch else None
            ),
            "next_scheduled_run": None,  # Could be calculated from schedule
            "db_url": (
                self.db_url[:20] + "..." if self.db_url else None
            ),  # Mask sensitive info
        }

    def start(
        self,
        price_interval_hours: int = 1,
        maintenance_hour: int = 2,
        days_back: int = 1,
        force_refresh: bool = False,
    ):
        """Start the scheduler service."""
        self.logger.info("🚀 Starting NSSM Market Data Scheduler...")
        self.logger.info(
            f"   Database: {self.db_url[:30]}..."
            if self.db_url
            else "No database configured"
        )
        self.logger.info(f"   Price fetch interval: {price_interval_hours} hour(s)")
        self.logger.info(f"   Days back: {days_back}")
        self.logger.info(f"   Force refresh: {force_refresh}")

        # Schedule hourly price fetching
        schedule.every(price_interval_hours).hours.at(":00").do(
            self.run_hourly_price_fetch_sync,
            days_back=days_back,
            force_refresh=force_refresh,
        )

        # Schedule daily maintenance
        schedule.every().day.at(f"{maintenance_hour:02d}:00").do(
            self.run_daily_maintenance_sync
        )

        self.running = True
        self.logger.info("📅 Scheduled jobs:")
        for job in schedule.jobs:
            self.logger.info(f"   {job}")

        try:
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            self.logger.info("⏹️  Scheduler stopped by user")
        except Exception as e:
            self.logger.error(f"💥 Scheduler error: {e}")
        finally:
            self.logger.info("👋 NSSM Market Data Scheduler stopped")

    def stop(self):
        """Stop the scheduler service."""
        self.running = False
        self.logger.info("🛑 Stopping scheduler...")

    async def run_once(
        self,
        tickers: Optional[List[str]] = None,
        days_back: int = 1,
        force_refresh: bool = False,
    ) -> dict:
        """Run price fetch once (useful for manual execution)."""
        try:
            self.logger.info("🔄 Running one-time price fetch...")

            results = fetch_market_prices(
                db_url=self.db_url,
                tickers=tickers,
                days_back=days_back,
                force_refresh=force_refresh,
                fallback_to_mock=self.fallback_to_mock,
            )

            total_stored = sum(results.values())
            successful_tickers = sum(1 for count in results.values() if count > 0)

            self.logger.info(
                f"✅ One-time fetch completed: {total_stored} data points "
                f"for {successful_tickers} tickers"
            )

            return {
                "success": True,
                "results": results,
                "total_stored": total_stored,
                "successful_tickers": successful_tickers,
            }

        except Exception as e:
            self.logger.error(f"💥 One-time fetch failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": {},
                "total_stored": 0,
                "successful_tickers": 0,
            }


def main():
    """Main entry point for the market data scheduler service."""
    import argparse

    parser = argparse.ArgumentParser(description="NSSM Market Data Scheduler")
    parser.add_argument("--db-url", help="Database URL (default: from environment)")
    parser.add_argument(
        "--interval-hours",
        type=int,
        default=1,
        help="Hours between price fetches (default: 1)",
    )
    parser.add_argument(
        "--maintenance-hour",
        type=int,
        default=2,
        help="Hour of day for maintenance (0-23, default: 2)",
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=1,
        help="Days of historical data to fetch (default: 1)",
    )
    parser.add_argument(
        "--force-refresh", action="store_true", help="Force refresh of existing data"
    )
    parser.add_argument(
        "--once", action="store_true", help="Run once and exit (for manual execution)"
    )
    parser.add_argument(
        "--tickers",
        nargs="*",
        help="Specific tickers to fetch (default: all from config)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    logger = logging.getLogger(__name__)

    try:
        logger.info("🌟 NSSM Market Data Scheduler starting...")

        scheduler = MarketDataScheduler(db_url=args.db_url)

        if args.once:
            # Run once and exit
            logger.info("Running one-time execution...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            result = loop.run_until_complete(
                scheduler.run_once(
                    tickers=args.tickers,
                    days_back=args.days_back,
                    force_refresh=args.force_refresh,
                )
            )
            loop.close()

            if result["success"]:
                logger.info("✅ One-time execution completed successfully")
                sys.exit(0)
            else:
                logger.error(f"❌ One-time execution failed: {result['error']}")
                sys.exit(1)
        else:
            # Start scheduler service
            scheduler.start(
                price_interval_hours=args.interval_hours,
                maintenance_hour=args.maintenance_hour,
                days_back=args.days_back,
                force_refresh=args.force_refresh,
            )

    except KeyboardInterrupt:
        logger.info("⏹️  Scheduler stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        import traceback

        logger.debug(f"Full traceback: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
