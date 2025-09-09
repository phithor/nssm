"""
Nordic Exchange Announcements Fetcher

This module fetches company announcements and filings from Nordic exchanges:
- Oslo Børs NewsWeb API
- Nasdaq OMX Nordic RSS feeds
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pytz
import requests
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from config import load_markets_config
from db.models import News

logger = logging.getLogger(__name__)


class NordicAnnouncementsFetcher:
    """Fetcher for Nordic exchange announcements and filings."""

    def __init__(self, db_url: str):
        """Initialize with database connection."""
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.markets_config = load_markets_config()
        self.oslo_tz = pytz.timezone("Europe/Oslo")
        self.utc_tz = pytz.UTC

        # Request session with timeout
        self.session = requests.Session()
        self.session.timeout = 30

    def _normalize_datetime(
        self, dt_str: str, source_tz: str = "Europe/Oslo"
    ) -> datetime:
        """Normalize datetime string to Oslo timezone."""
        try:
            # Try parsing ISO format first
            if "T" in dt_str:
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            else:
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")

            # Assume source timezone if naive
            if dt.tzinfo is None:
                source_tz_obj = pytz.timezone(source_tz)
                dt = source_tz_obj.localize(dt)

            # Convert to Oslo timezone
            return dt.astimezone(self.oslo_tz)

        except Exception as e:
            logger.warning(f"Failed to parse datetime '{dt_str}': {e}")
            return datetime.now(self.oslo_tz)

    def fetch_oslo_bors_newsweb(
        self, issuer_id: str, days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """Fetch announcements from Oslo Børs NewsWeb using Selenium scraper."""
        announcements = []

        try:
            # Import the Oslo Børs scraper
            from scraper.oslobors import OsloBorsScraper

            # Initialize the scraper
            scraper = OsloBorsScraper()

            # Search for announcements for the specific issuer
            raw_announcements = scraper.search_announcements(issuer_id=issuer_id)

            # Filter by date if needed
            cutoff_date = datetime.now(self.oslo_tz) - timedelta(days=days_back)

            for item in raw_announcements:
                # Parse the date from the announcement
                try:
                    if item.get("parsed_date"):
                        published_at = item["parsed_date"]
                        if published_at.tzinfo is None:
                            published_at = self.oslo_tz.localize(published_at)
                    else:
                        # Parse the date string
                        date_str = item.get("date_time", "")
                        published_at = datetime.strptime(date_str, "%d.%m.%Y %H:%M")
                        published_at = self.oslo_tz.localize(published_at)
                except Exception as e:
                    logger.warning(f"Failed to parse date for announcement: {e}")
                    published_at = datetime.now(self.oslo_tz)

                # Skip if too old
                if published_at < cutoff_date:
                    continue

                # Get detailed information if available
                details = None
                if item.get("url"):
                    try:
                        details = scraper.fetch_announcement_details(item["url"])
                    except Exception as e:
                        logger.warning(
                            f"Failed to fetch details for {item['url']}: {e}"
                        )

                announcement = {
                    "ticker": issuer_id,
                    "headline": item.get("title", ""),
                    "summary": (
                        details.get("content", "")[:500] if details else ""
                    ),  # First 500 chars as summary
                    "body_html": details.get("content", "") if details else "",
                    "link": item.get("url", ""),
                    "published_at": published_at,
                    "source": "oslobors",
                    "category": "filing",
                    "importance": 1.0,  # Company filings are important
                    "market": item.get("market", ""),
                    "category_detail": item.get("category", ""),
                    "attachments_count": item.get("attachments_count", 0),
                    "message_id": details.get("MessageID", "") if details else "",
                    "issuer_name": details.get("issuer_name", "") if details else "",
                }

                announcements.append(announcement)

            logger.info(
                f"Fetched {len(announcements)} announcements from Oslo Børs for "
                f"{issuer_id}"
            )

        except Exception as e:
            logger.error(f"Error fetching Oslo Børs announcements for {issuer_id}: {e}")

        return announcements

    def fetch_nasdaq_nordic_rss(self, exchange: str, ric: str) -> List[Dict[str, Any]]:
        """Fetch announcements from Nasdaq OMX Nordic RSS feeds."""
        announcements = []

        try:
            # RSS fetching is deprecated and not implemented
            logger.warning(
                f"RSS fetching for {exchange} is deprecated and not implemented."
            )
            return []

        except Exception as e:
            logger.error(f"Error fetching Nasdaq RSS announcements for {ric}: {e}")

        return announcements

    def _upsert_announcement(self, session, announcement: Dict[str, Any]) -> bool:
        """Upsert an announcement, returning True if inserted/updated."""
        try:
            # Check for existing item
            existing = session.execute(
                select(News).where(
                    News.ticker == announcement["ticker"],
                    News.headline == announcement["headline"],
                    News.published_at == announcement["published_at"],
                )
            ).scalar_one_or_none()

            if existing:
                # Update existing item if needed
                updated = False
                for key, value in announcement.items():
                    if key != "id" and getattr(existing, key) != value:
                        setattr(existing, key, value)
                        updated = True

                if updated:
                    logger.debug(
                        f"Updated existing announcement: {announcement['headline']}"
                    )
                    return True
                return False

            # Insert new item
            news = News(**announcement)
            session.add(news)
            session.commit()
            logger.debug(f"Inserted new announcement: {announcement['headline']}")
            return True

        except IntegrityError:
            session.rollback()
            logger.debug(f"Duplicate announcement skipped: {announcement['headline']}")
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error upserting announcement: {e}")
            return False

    def store_announcements_batch(self, announcements: List[Dict[str, Any]]) -> int:
        """Store a batch of announcements with upsert logic."""
        stored_count = 0

        with self.SessionLocal() as session:
            for announcement in announcements:
                if self._upsert_announcement(session, announcement):
                    stored_count += 1

        return stored_count

    async def fetch_and_store_announcements(self, days_back: int = 7) -> Dict[str, int]:
        """Fetch and store announcements from all configured sources."""
        total_stored = 0
        errors = []

        # Get configured exchanges and their tickers
        exchanges = self.markets_config.get("exchanges", {})

        for exchange_id, exchange_config in exchanges.items():
            try:
                tickers = exchange_config.get("tickers", [])
                if not tickers:
                    continue

                logger.info(f"Processing {len(tickers)} tickers for {exchange_id}")

                for ticker in tickers:
                    try:
                        # Fetch announcements based on exchange type
                        if exchange_id == "OSE":
                            announcements = self.fetch_oslo_bors_newsweb(
                                ticker, days_back
                            )
                        else:
                            # For other exchanges, use RSS (if implemented)
                            announcements = self.fetch_nasdaq_nordic_rss(
                                exchange_id, ticker
                            )

                        if announcements:
                            stored_count = self.store_announcements_batch(announcements)
                            total_stored += stored_count
                            logger.info(
                                f"Stored {stored_count} announcements for {ticker} "
                                f"from {exchange_id}"
                            )

                    except Exception as e:
                        error_msg = f"Error processing {ticker} from {exchange_id}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)

            except Exception as e:
                error_msg = f"Error processing exchange {exchange_id}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        logger.info(f"Total announcements stored: {total_stored}")
        if errors:
            logger.warning(f"Encountered {len(errors)} errors during processing")

        return {"stored": total_stored, "errors": len(errors)}

    async def get_sentiment_tracked_tickers(self) -> List[str]:
        """Get unique tickers from sentiment aggregation table."""
        try:
            from sqlalchemy import distinct, select

            from db.models import SentimentAgg

            with self.SessionLocal() as session:
                # Get unique tickers from sentiment aggregation
                tickers = (
                    session.execute(
                        select(distinct(SentimentAgg.ticker))
                        .where(SentimentAgg.ticker.isnot(None))
                        .order_by(SentimentAgg.ticker)
                    )
                    .scalars()
                    .all()
                )

                return list(tickers)

        except Exception as e:
            logger.error(f"Error getting sentiment-tracked tickers: {e}")
            return []

    async def fetch_and_store_announcements_for_tickers(
        self, tickers: List[str], days_back: int = 7
    ) -> Dict[str, int]:
        """Fetch and store announcements for specific tickers."""
        total_stored = 0
        errors = []

        for ticker in tickers:
            try:
                logger.info(f"Fetching announcements for ticker: {ticker}")

                # Fetch Oslo Børs announcements for this ticker
                announcements = self.fetch_oslo_bors_newsweb(ticker, days_back)

                # Store announcements
                stored_count = 0
                for announcement in announcements:
                    if self._upsert_news_item(announcement):
                        stored_count += 1

                total_stored += stored_count
                logger.info(f"Stored {stored_count} announcements for {ticker}")

            except Exception as e:
                logger.error(f"Error fetching announcements for {ticker}: {e}")
                errors.append(f"{ticker}: {e}")

        if errors:
            logger.warning(f"Encountered {len(errors)} errors during processing")

        return {"stored": total_stored, "errors": len(errors)}


async def fetch_nordic_announcements(
    db_url: str, tickers: Optional[List[str]] = None, days_back: int = 7
) -> Dict[str, int]:
    """
    Main function to fetch Nordic exchange announcements.

    Args:
        db_url: Database connection URL
        tickers: Optional list of tickers to fetch news for (if None, fetches for all)
        days_back: Number of days back to fetch announcements

    Returns:
        Dictionary mapping sources to number of items stored
    """
    fetcher = NordicAnnouncementsFetcher(db_url)

    # If no tickers specified, get tickers from sentiment aggregation table
    if tickers is None:
        tickers = await fetcher.get_sentiment_tracked_tickers()
        logger.info(
            f"No tickers specified, using {len(tickers)} tickers from "
            f"sentiment aggregation"
        )

    if not tickers:
        logger.warning("No tickers available for news fetching")
        return {"oslobors": 0}

    logger.info(f"Fetching Oslo Børs announcements for tickers: {tickers}")
    return await fetcher.fetch_and_store_announcements_for_tickers(tickers, days_back)
