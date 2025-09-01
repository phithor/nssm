"""
OpenBB News Ingestion Wrapper

This module wraps OpenBB news endpoints to fetch Scandinavian stock-related news.
Handles timezone conversion, duplicate prevention, and data persistence.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, Dict, List, Optional

import pytz
import requests
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from config import load_markets_config
from db.models import News

logger = logging.getLogger(__name__)

# Rate limiting semaphore
semaphore = asyncio.Semaphore(50)  # Max 50 concurrent requests
call_timestamps = []  # Track call timestamps for rate limiting


class OpenBBNewsFetcher:
    """Fetcher for OpenBB news data with rate limiting and caching."""

    def __init__(self, db_url: str):
        """Initialize with database connection."""
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.markets_config = load_markets_config()
        self.oslo_tz = pytz.timezone("Europe/Oslo")
        self.utc_tz = pytz.UTC

    def _rate_limit_wait(self) -> None:
        """Enforce rate limiting (60 calls per minute)."""
        now = time.time()
        # Remove timestamps older than 1 minute
        global call_timestamps
        call_timestamps = [ts for ts in call_timestamps if now - ts < 60]

        if len(call_timestamps) >= 60:
            # Wait until the oldest call is more than 1 minute old
            sleep_time = 60 - (now - call_timestamps[0])
            if sleep_time > 0:
                logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)

        call_timestamps.append(now)

    async def fetch_news_for_ticker(
        self, ticker: str, days_back: int = 1
    ) -> List[Dict[str, Any]]:
        """Fetch news for a specific ticker using direct API calls."""
        async with semaphore:
            try:
                self._rate_limit_wait()

                start_date = datetime.now(self.utc_tz) - timedelta(days=days_back)

                # TODO: Replace with actual financial news API (e.g., Alpha Vantage, NewsAPI, or OpenBB)
                # For now, using a placeholder implementation that demonstrates the structure

                # Example API endpoints that could be used:
                # - NewsAPI: https://newsapi.org/v2/everything?q={ticker}+stock&from={start_date}
                # - Alpha Vantage: https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}
                # - Financial Modeling Prep: https://financialmodelingprep.com/api/v3/stock_news?tickers={ticker}

                # Placeholder implementation - replace with real API calls
                news_items = await self._fetch_news_from_api(ticker, start_date)

                logger.info(f"Fetched {len(news_items)} news items for {ticker}")
                return news_items

            except Exception as e:
                logger.error(f"Error fetching news for {ticker}: {e}")
                return []

    async def _fetch_news_from_api(
        self, ticker: str, start_date: datetime
    ) -> List[Dict[str, Any]]:
        """Fetch news from external API (placeholder implementation)."""
        # TODO: Implement actual API integration
        # This is a placeholder that returns mock data to demonstrate the structure

        # Simulate API delay
        await asyncio.sleep(0.1)

        # Mock news items - replace with real API calls
        mock_news = [
            {
                "ticker": ticker,
                "headline": f"Stock Market Update: {ticker} Shows Strong Performance",
                "summary": f"Latest market analysis shows positive momentum for {ticker} with increased trading volume.",
                "link": f"https://example.com/news/{ticker.lower()}-update",
                "published_at": datetime.now(self.oslo_tz) - timedelta(hours=2),
                "source": "openbb",
                "category": "news",
                "importance": 0.6,
            },
            {
                "ticker": ticker,
                "headline": f"Quarterly Earnings Report: {ticker} Beats Expectations",
                "summary": f"{ticker} reported stronger than expected quarterly earnings, driving market optimism.",
                "link": f"https://example.com/news/{ticker.lower()}-earnings",
                "published_at": datetime.now(self.oslo_tz) - timedelta(hours=4),
                "source": "openbb",
                "category": "news",
                "importance": 0.8,
            },
        ]

        return mock_news

    def _upsert_news_item(self, session, news_item: Dict[str, Any]) -> bool:
        """Upsert a news item, returning True if inserted/updated."""
        try:
            # Check for existing item
            existing = session.execute(
                select(News).where(
                    News.ticker == news_item["ticker"],
                    News.headline == news_item["headline"],
                    News.published_at == news_item["published_at"],
                )
            ).scalar_one_or_none()

            if existing:
                # Update existing item if needed
                updated = False
                for key, value in news_item.items():
                    if key != "id" and getattr(existing, key) != value:
                        setattr(existing, key, value)
                        updated = True

                if updated:
                    logger.debug(f"Updated existing news item: {news_item['headline']}")
                    return True
                return False

            # Insert new item
            news = News(**news_item)
            session.add(news)
            session.commit()
            logger.debug(f"Inserted new news item: {news_item['headline']}")
            return True

        except IntegrityError:
            session.rollback()
            logger.debug(f"Duplicate news item skipped: {news_item['headline']}")
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error upserting news item: {e}")
            return False

    def store_news_batch(self, news_items: List[Dict[str, Any]]) -> int:
        """Store a batch of news items with upsert logic."""
        stored_count = 0

        with self.SessionLocal() as session:
            for item in news_items:
                if self._upsert_news_item(session, item):
                    stored_count += 1

        return stored_count

    async def fetch_and_store_all_tickers(self, days_back: int = 1) -> Dict[str, int]:
        """Fetch news for all Scandinavian tickers and store them."""
        results = {}

        # Get all tickers from market config
        tickers = []
        for market_data in self.markets_config.get("markets", {}).values():
            if "ticker" in market_data:
                tickers.append(market_data["ticker"])

        logger.info(f"Fetching news for {len(tickers)} tickers")

        # Fetch news for all tickers concurrently
        tasks = [self.fetch_news_for_ticker(ticker, days_back) for ticker in tickers]
        all_news_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and store
        for ticker, news_result in zip(tickers, all_news_results):
            if isinstance(news_result, Exception):
                logger.error(f"Failed to fetch news for {ticker}: {news_result}")
                results[ticker] = 0
            else:
                stored_count = self.store_news_batch(news_result)
                results[ticker] = stored_count
                logger.info(f"Stored {stored_count} news items for {ticker}")

        total_stored = sum(results.values())
        logger.info(f"Total news items stored: {total_stored}")

        return results


@lru_cache(maxsize=100)
def load_markets_config():
    """Load markets configuration with caching."""
    import os

    import yaml

    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "markets.yml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


async def fetch_openbb_news(
    db_url: str, tickers: Optional[List[str]] = None, days_back: int = 1
) -> Dict[str, int]:
    """
    Main function to fetch OpenBB news.

    Args:
        db_url: Database connection URL
        tickers: Optional list of tickers to fetch (default: all from config)
        days_back: Number of days back to fetch news

    Returns:
        Dictionary mapping tickers to number of items stored
    """
    fetcher = OpenBBNewsFetcher(db_url)

    if tickers:
        # Fetch specific tickers
        tasks = [fetcher.fetch_news_for_ticker(ticker, days_back) for ticker in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        stored_results = {}
        for ticker, result in zip(tickers, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch news for {ticker}: {result}")
                stored_results[ticker] = 0
            else:
                stored_count = fetcher.store_news_batch(result)
                stored_results[ticker] = stored_count

        return stored_results
    else:
        # Fetch all tickers from config
        return await fetcher.fetch_and_store_all_tickers(days_back)
