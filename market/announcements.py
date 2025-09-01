"""
Nordic Exchange Announcements Fetcher

This module fetches company announcements and filings from Nordic exchanges:
- Oslo Børs NewsWeb API
- Nasdaq OMX Nordic RSS feeds
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import feedparser
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
        """Fetch announcements from Oslo Børs NewsWeb API."""
        announcements = []

        try:
            base_url = self.markets_config["exchanges"]["OSE"]["newsweb_url"]
            from_date = (
                datetime.now(self.oslo_tz) - timedelta(days=days_back)
            ).strftime("%Y-%m-%d")

            url = f"{base_url}/news"
            params = {"issuerId": issuer_id, "from": from_date, "lang": "en"}

            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            for item in data.get("news", []):
                published_at = self._normalize_datetime(item.get("publishDate", ""))

                announcement = {
                    "ticker": issuer_id,  # Using issuer ID as ticker for now
                    "headline": item.get("headline", ""),
                    "summary": item.get("lead", ""),
                    "body_html": item.get("body", ""),
                    "link": item.get("url", ""),
                    "published_at": published_at,
                    "source": "oslobors",
                    "category": "filing",
                    "importance": 1.0,  # Company filings are important
                }

                announcements.append(announcement)

            logger.info(
                f"Fetched {len(announcements)} announcements from Oslo Børs for {issuer_id}"
            )

        except Exception as e:
            logger.error(f"Error fetching Oslo Børs announcements for {issuer_id}: {e}")

        return announcements

    def fetch_nasdaq_nordic_rss(self, exchange: str, ric: str) -> List[Dict[str, Any]]:
        """Fetch announcements from Nasdaq OMX Nordic RSS feeds."""
        announcements = []

        try:
            base_url = self.markets_config["exchanges"][exchange]["rss_url"]
            rss_url = f"{base_url}/NewsRelease?Instrument={ric}"

            feed = feedparser.parse(rss_url)

            for entry in feed.entries:
                published_at = self._normalize_datetime(
                    entry.get("published", entry.get("updated", "")),
                    self.markets_config["exchanges"][exchange]["timezone"],
                )

                # Extract RIC from entry or use provided one
                ticker = entry.get("ric", ric.split(".")[0])

                announcement = {
                    "ticker": ticker,
                    "headline": entry.get("title", ""),
                    "summary": entry.get("summary", ""),
                    "body_html": (
                        entry.get("content", [{}])[0].get("value", "")
                        if entry.get("content")
                        else ""
                    ),
                    "link": entry.get("link", ""),
                    "published_at": published_at,
                    "source": "nasdaq",
                    "category": "filing",
                    "importance": 1.0,
                }

                announcements.append(announcement)

            logger.info(
                f"Fetched {len(announcements)} RSS announcements from {exchange} for {ric}"
            )

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
        """Fetch announcements from all Nordic exchanges and store them."""
        results = {}

        # Oslo Børs NewsWeb - fetch for major companies
        oslo_companies = [
            ("EQNR", "equinor"),  # Example issuer IDs - would need actual mapping
            ("TEL", "telenor"),
            ("DNB", "dnb"),
        ]

        for ticker, issuer_id in oslo_companies:
            announcements = self.fetch_oslo_bors_newsweb(issuer_id, days_back)
            stored_count = self.store_announcements_batch(announcements)
            results[f"{ticker}_oslobors"] = stored_count
            logger.info(f"Stored {stored_count} Oslo Børs announcements for {ticker}")

        # Nasdaq OMX Nordic RSS feeds
        nasdaq_exchanges = ["STO", "CPH", "HEX"]
        major_tickers = [
            "VOLV-B.ST",
            "ERIC-B.ST",
            "HM-B.ST",  # Stockholm
            "NOVO-B.CO",
            "DANSKE.CO",  # Copenhagen
            "NOKIA.HE",
            "NESTE.HE",  # Helsinki
        ]

        for ric in major_tickers:
            exchange = ric.split(".")[-1]
            if exchange in ["ST", "CO", "HE"]:
                exchange_map = {"ST": "STO", "CO": "CPH", "HE": "HEX"}
                exchange_name = exchange_map[exchange]

                announcements = self.fetch_nasdaq_nordic_rss(exchange_name, ric)
                stored_count = self.store_announcements_batch(announcements)
                results[f"{ric}_nasdaq"] = stored_count
                logger.info(f"Stored {stored_count} Nasdaq RSS announcements for {ric}")

        total_stored = sum(results.values())
        logger.info(f"Total announcements stored: {total_stored}")

        return results


async def fetch_nordic_announcements(db_url: str, days_back: int = 7) -> Dict[str, int]:
    """
    Main function to fetch Nordic exchange announcements.

    Args:
        db_url: Database connection URL
        days_back: Number of days back to fetch announcements

    Returns:
        Dictionary mapping sources to number of items stored
    """
    fetcher = NordicAnnouncementsFetcher(db_url)
    return await fetcher.fetch_and_store_announcements(days_back)
