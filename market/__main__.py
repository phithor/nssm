"""
News Sync CLI Entry Point

Command-line interface for syncing news and announcements from Scandinavian markets.
Supports incremental fetching, backfilling, and scheduled execution.
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from typing import List, Optional

import click
import pytz
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from market.announcements import fetch_nordic_announcements
from market.data import OpenBBYahooFinancePriceFetcher, fetch_market_prices
from market.news_openbb import fetch_openbb_news
from market.scheduler import MarketDataScheduler
from market.state_management import NewsStateManager, get_state_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_duration(duration_str: str) -> int:
    """Parse duration string like '7d', '24h', '30m' into days."""
    if duration_str.endswith("d"):
        return int(duration_str[:-1])
    elif duration_str.endswith("h"):
        return int(duration_str[:-1]) // 24
    elif duration_str.endswith("m"):
        return int(duration_str[:-1]) // (24 * 60)
    else:
        return int(duration_str)


@click.group()
@click.option(
    "--db-url", envvar="DATABASE_URL", required=True, help="Database connection URL"
)
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="Logging level",
)
@click.pass_context
def cli(ctx: click.Context, db_url: str, log_level: str) -> None:
    """Market data CLI for Scandinavian markets (news and prices)."""
    ctx.ensure_object(dict)
    ctx.obj["db_url"] = db_url

    # Set log level
    numeric_level = getattr(logging, log_level.upper(), None)
    logging.getLogger().setLevel(numeric_level)


@cli.command()
@click.option(
    "--tickers",
    multiple=True,
    help="Specific tickers to fetch (default: all from config)",
)
@click.option(
    "--days-back", type=int, default=1, help="Number of days back to fetch news"
)
@click.option(
    "--sources",
    multiple=True,
    type=click.Choice(["openbb", "nordic"]),
    help="Specific sources to fetch from (default: all)",
)
@click.option("--force", is_flag=True, help="Force fetch even if recently fetched")
@click.pass_context
def run(
    ctx: click.Context,
    tickers: List[str],
    days_back: int,
    sources: List[str],
    force: bool,
) -> None:
    """Run news synchronization."""
    db_url = ctx.obj["db_url"]

    async def _run_sync():
        results = {}

        # Determine which sources to fetch
        all_sources = ["openbb", "nordic"]
        if sources:
            fetch_sources = list(sources)
        else:
            fetch_sources = all_sources

        # Fetch from OpenBB
        if "openbb" in fetch_sources:
            logger.info("Fetching news from OpenBB...")
            try:
                openbb_results = await fetch_openbb_news(
                    db_url=db_url,
                    tickers=list(tickers) if tickers else None,
                    days_back=days_back,
                )
                results["openbb"] = openbb_results
                logger.info(f"OpenBB fetch completed: {openbb_results}")
            except Exception as e:
                logger.error(f"OpenBB fetch failed: {e}")
                results["openbb"] = {}

        # Fetch from Nordic exchanges
        if "nordic" in fetch_sources:
            logger.info("Fetching announcements from Nordic exchanges...")
            try:
                nordic_results = await fetch_nordic_announcements(
                    db_url=db_url, days_back=days_back
                )
                results["nordic"] = nordic_results
                logger.info(f"Nordic announcements fetch completed: {nordic_results}")
            except Exception as e:
                logger.error(f"Nordic announcements fetch failed: {e}")
                results["nordic"] = {}

        return results

    # Run async function
    results = asyncio.run(_run_sync())

    # Print summary
    total_items = 0
    for source, source_results in results.items():
        if isinstance(source_results, dict):
            source_total = sum(source_results.values())
            total_items += source_total
            click.echo(f"{source}: {source_total} items stored")

    click.echo(f"\nTotal items processed: {total_items}")


@cli.command()
@click.option(
    "--duration", default="7d", help="Backfill duration (e.g., 7d, 24h, 168h)"
)
@click.option(
    "--sources",
    multiple=True,
    type=click.Choice(["openbb", "nordic"]),
    help="Specific sources to backfill (default: all)",
)
@click.pass_context
def backfill(ctx: click.Context, duration: str, sources: List[str]) -> None:
    """Backfill historical news data."""
    db_url = ctx.obj["db_url"]
    days_back = parse_duration(duration)

    logger.info(f"Starting backfill for {days_back} days")

    async def _run_backfill():
        results = {}

        # Determine which sources to backfill
        all_sources = ["openbb", "nordic"]
        if sources:
            backfill_sources = list(sources)
        else:
            backfill_sources = all_sources

        # Backfill OpenBB
        if "openbb" in backfill_sources:
            logger.info(f"Backfilling OpenBB news for {days_back} days...")
            try:
                openbb_results = await fetch_openbb_news(
                    db_url=db_url, days_back=days_back
                )
                results["openbb"] = openbb_results
                logger.info(f"OpenBB backfill completed: {openbb_results}")
            except Exception as e:
                logger.error(f"OpenBB backfill failed: {e}")
                results["openbb"] = {}

        # Backfill Nordic exchanges
        if "nordic" in backfill_sources:
            logger.info(f"Backfilling Nordic announcements for {days_back} days...")
            try:
                nordic_results = await fetch_nordic_announcements(
                    db_url=db_url, days_back=days_back
                )
                results["nordic"] = nordic_results
                logger.info(f"Nordic backfill completed: {nordic_results}")
            except Exception as e:
                logger.error(f"Nordic backfill failed: {e}")
                results["nordic"] = {}

        return results

    # Run async backfill
    results = asyncio.run(_run_backfill())

    # Print summary
    total_items = 0
    for source, source_results in results.items():
        if isinstance(source_results, dict):
            source_total = sum(source_results.values())
            total_items += source_total
            click.echo(f"{source}: {source_total} items stored")

    click.echo(f"\nBackfill completed. Total items: {total_items}")


@cli.command()
@click.option(
    "--sources",
    multiple=True,
    type=click.Choice(["openbb", "oslobors", "nasdaq_sto", "nasdaq_cph", "nasdaq_hex"]),
    help="Specific sources to reset (default: all)",
)
@click.pass_context
def reset(ctx: click.Context, sources: List[str]) -> None:
    """Reset fetch state for sources."""
    manager = get_state_manager()

    if sources:
        for source in sources:
            manager.reset_source(source)
            click.echo(f"Reset state for: {source}")
    else:
        manager.reset_all()
        click.echo("Reset all source states")


@cli.command()
def status() -> None:
    """Show current fetch status and statistics."""
    manager = get_state_manager()
    stats = manager.get_stats()

    click.echo("News Sync Status")
    click.echo("=" * 40)
    click.echo(f"Total Sources: {stats['total_sources']}")
    click.echo(f"Last Updated: {stats['last_updated']}")
    click.echo()

    click.echo("Source Statistics:")
    for source, source_stats in stats["source_stats"].items():
        click.echo(f"  {source}:")
        click.echo(f"    Total Fetches: {source_stats['total_fetches']}")
        click.echo(f"    Has Last Fetch: {source_stats['has_last_fetch']}")
        click.echo(f"    Has Last Backfill: {source_stats['has_last_backfill']}")
        click.echo()


@cli.command()
@click.option(
    "--interval-minutes",
    type=int,
    default=10,
    help="Interval between sync runs in minutes",
)
@click.option(
    "--sources",
    multiple=True,
    type=click.Choice(["openbb", "nordic"]),
    help="Sources to sync (default: all)",
)
@click.pass_context
def schedule(ctx: click.Context, interval_minutes: int, sources: List[str]) -> None:
    """Run scheduled news synchronization."""
    db_url = ctx.obj["db_url"]

    try:
        import schedule as scheduler
    except ImportError:
        click.echo("schedule package not installed. Install with: pip install schedule")
        sys.exit(1)

    def sync_job():
        """Scheduled sync job."""
        click.echo(f"[{datetime.now()}] Running scheduled sync...")
        try:
            # Run the sync
            result = asyncio.run(run_sync_job(db_url, sources))
            click.echo(f"[{datetime.now()}] Sync completed: {result}")
        except Exception as e:
            click.echo(f"[{datetime.now()}] Sync failed: {e}")

    async def run_sync_job(db_url: str, sources: List[str]) -> dict:
        """Run sync job asynchronously."""
        results = {}

        fetch_sources = list(sources) if sources else ["openbb", "nordic"]

        if "openbb" in fetch_sources:
            openbb_results = await fetch_openbb_news(db_url)
            results["openbb"] = openbb_results

        if "nordic" in fetch_sources:
            nordic_results = await fetch_nordic_announcements(db_url)
            results["nordic"] = nordic_results

        return results

    # Schedule the job
    scheduler.every(interval_minutes).minutes.do(sync_job)

    click.echo(f"Scheduled news sync every {interval_minutes} minutes")
    click.echo("Press Ctrl+C to stop")

    try:
        while True:
            scheduler.run_pending()
            asyncio.sleep(1)
    except KeyboardInterrupt:
        click.echo("\nScheduler stopped")


# Price Data Commands
@cli.command()
@click.option(
    "--tickers",
    multiple=True,
    help="Specific tickers to fetch (default: all from config)",
)
@click.option(
    "--days-back", type=int, default=1, help="Number of days back to fetch prices"
)
@click.option("--force-refresh", is_flag=True, help="Force refresh of existing data")
@click.option(
    "--mock-fallback",
    is_flag=True,
    help="Use mock data if OpenBB API is not available (for development)",
)
@click.pass_context
def prices(
    ctx: click.Context,
    tickers: List[str],
    days_back: int,
    force_refresh: bool,
    mock_fallback: bool,
) -> None:
    """Fetch market price data for Scandinavian tickers."""
    db_url = ctx.obj["db_url"]

    try:
        if mock_fallback:
            click.echo("🧪 Using mock data fallback mode")

        results = fetch_market_prices(
            db_url=db_url,
            tickers=list(tickers) if tickers else None,
            days_back=days_back,
            force_refresh=force_refresh,
            fallback_to_mock=mock_fallback,
        )

        total_stored = sum(results.values())
        successful_tickers = sum(1 for count in results.values() if count > 0)

        click.echo(f"✅ Price fetch completed: {total_stored} data points stored")
        click.echo(f"   Tickers processed: {successful_tickers}/{len(results)}")

        # Show results per ticker
        for ticker, count in results.items():
            if count > 0:
                click.echo(f"   {ticker}: {count} data points")
            else:
                click.echo(f"   {ticker}: no new data")

    except Exception as e:
        logger.error(f"Price fetch failed: {e}")
        click.echo(f"❌ Price fetch failed: {e}", err=True)
        click.echo("💡 Try using --mock-fallback for development/testing")
        sys.exit(1)


@cli.command()
@click.option(
    "--interval-hours",
    type=int,
    default=1,
    help="Hours between price fetches (default: 1)",
)
@click.option(
    "--maintenance-hour",
    type=int,
    default=2,
    help="Hour of day for maintenance (0-23, default: 2)",
)
@click.option(
    "--days-back",
    type=int,
    default=1,
    help="Days of historical data to fetch (default: 1)",
)
@click.option("--force-refresh", is_flag=True, help="Force refresh of existing data")
@click.option(
    "--mock-fallback",
    is_flag=True,
    help="Use mock data if OpenBB API is not available (for development)",
)
@click.option("--once", is_flag=True, help="Run once and exit (for testing)")
@click.pass_context
def schedule_prices(
    ctx: click.Context,
    interval_hours: int,
    maintenance_hour: int,
    days_back: int,
    force_refresh: bool,
    mock_fallback: bool,
    once: bool,
) -> None:
    """Run scheduled market price data fetching."""
    db_url = ctx.obj["db_url"]

    try:
        scheduler = MarketDataScheduler(db_url=db_url, fallback_to_mock=mock_fallback)

        if once:
            # Run once and exit
            click.echo("Running one-time price fetch...")

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            result = loop.run_until_complete(
                scheduler.run_once(days_back=days_back, force_refresh=force_refresh)
            )
            loop.close()

            if result["success"]:
                click.echo(
                    f"✅ One-time execution completed: {result['total_stored']} data points stored"
                )
                sys.exit(0)
            else:
                click.echo(f"❌ One-time execution failed: {result['error']}", err=True)
                sys.exit(1)
        else:
            # Start scheduler service
            click.echo(
                f"Starting price data scheduler (interval: {interval_hours}h)..."
            )
            scheduler.start(
                price_interval_hours=interval_hours,
                maintenance_hour=maintenance_hour,
                days_back=days_back,
                force_refresh=force_refresh,
            )

    except KeyboardInterrupt:
        click.echo("\nScheduler stopped")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
        click.echo(f"❌ Scheduler failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--tickers",
    multiple=True,
    help="Specific tickers to check (default: all from config)",
)
@click.pass_context
def price_status(ctx: click.Context, tickers: List[str]) -> None:
    """Show current price data status and statistics."""
    db_url = ctx.obj["db_url"]

    try:
        from sqlalchemy import create_engine, func, select
        from sqlalchemy.orm import sessionmaker

        from db.models import MarketPrice

        engine = create_engine(db_url)
        SessionLocal = sessionmaker(bind=engine)

        with SessionLocal() as session:
            click.echo("Market Price Data Status")
            click.echo("=" * 50)

            # Overall statistics
            total_count = session.execute(
                select(func.count(MarketPrice.id))
            ).scalar_one()

            unique_tickers = session.execute(
                select(func.count(func.distinct(MarketPrice.ticker)))
            ).scalar_one()

            latest_timestamp = session.execute(
                select(func.max(MarketPrice.timestamp))
            ).scalar_one()

            click.echo(f"Total price records: {total_count}")
            click.echo(f"Unique tickers: {unique_tickers}")
            click.echo(f"Latest data timestamp: {latest_timestamp}")

            # Per-ticker statistics
            if tickers:
                ticker_list = list(tickers)
            else:
                # Get all tickers from config
                from config import load_markets_config

                config = load_markets_config()
                ticker_list = []
                for market_data in config.get("markets", {}).values():
                    if "ticker" in market_data:
                        ticker_list.append(market_data["ticker"])

            click.echo("\nPer-Ticker Statistics:")
            click.echo("-" * 50)

            for ticker in ticker_list:
                count = session.execute(
                    select(func.count(MarketPrice.id)).where(
                        MarketPrice.ticker == ticker
                    )
                ).scalar_one()

                latest = session.execute(
                    select(func.max(MarketPrice.timestamp)).where(
                        MarketPrice.ticker == ticker
                    )
                ).scalar_one()

                click.echo(f"  {ticker}:")
                click.echo(f"    Records: {count}")
                click.echo(f"    Latest: {latest}")
                click.echo()

    except Exception as e:
        logger.error(f"Status check failed: {e}")
        click.echo(f"❌ Status check failed: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
