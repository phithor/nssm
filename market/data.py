"""
OpenBB Yahoo Finance Price Data Integration

This module fetches market price data using OpenBB with yfinance provider (free, no API key required)
and stores it in the database. Handles rate limiting, retries, and data normalization
for Scandinavian markets.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

# Import pandas for data processing (will be imported when needed)
import pandas as pd
import pytz
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import load_markets_config
from db.models import MarketPrice

logger = logging.getLogger(__name__)

# Rate limiting semaphore - OpenBB with yfinance provider
RATE_LIMIT_SEMAPHORE = asyncio.Semaphore(30)  # Conservative limit for OpenBB yfinance
call_timestamps = []  # Track call timestamps for rate limiting


def _rate_limit_wait() -> None:
    """Enforce rate limiting (30 calls per minute max for OpenBB yfinance)."""
    now = time.time()
    # Remove timestamps older than 1 minute
    global call_timestamps
    call_timestamps = [ts for ts in call_timestamps if now - ts < 60]

    if len(call_timestamps) >= 30:
        # Wait until the oldest call is more than 1 minute old
        sleep_time = 60 - (now - call_timestamps[0])
        if sleep_time > 0:
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

    call_timestamps.append(now)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    reraise=True,
)
async def _fetch_price_with_retry(
    ticker: str, start_date: datetime, end_date: datetime
) -> Optional[Dict[str, Any]]:
    """Fetch price data for a ticker with retry logic using OpenBB with yfinance provider."""
    async with RATE_LIMIT_SEMAPHORE:
        try:
            _rate_limit_wait()

            # Import OpenBB here to avoid import errors if not installed
            from openbb import obb

            logger.debug(
                f"Fetching OpenBB Yahoo Finance data for {ticker} from {start_date} to {end_date}"
            )

            try:
                # Convert ticker to Yahoo Finance format if needed
                yahoo_ticker = _convert_to_yahoo_ticker(ticker)

                # Fetch hourly price data using OpenBB with yfinance provider
                response = obb.equity.price.historical(
                    symbol=yahoo_ticker,
                    provider="yfinance",
                    start_date=start_date.date(),
                    end_date=end_date.date(),
                    interval="1h",
                    extended_hours=False,  # Exclude pre/post market data
                )

                # Convert to DataFrame
                df = response.to_df()

                if df.empty:
                    logger.warning(
                        f"No data returned from OpenBB yfinance for {ticker}"
                    )
                    return None

                # Convert to our format
                prices = []
                for timestamp, row in df.iterrows():
                    # Convert pandas Timestamp to datetime
                    if hasattr(timestamp, "to_pydatetime"):
                        timestamp = timestamp.to_pydatetime()
                    else:
                        timestamp = timestamp

                    # Ensure timestamp is UTC
                    if timestamp.tzinfo is None:
                        timestamp = pytz.UTC.localize(timestamp)
                    else:
                        timestamp = timestamp.astimezone(pytz.UTC)

                    prices.append(
                        {
                            "timestamp": timestamp,
                            "price": float(row["close"]),
                            "volume": (
                                int(row["volume"])
                                if not pd.isna(row["volume"])
                                else None
                            ),
                            "high": (
                                float(row["high"]) if not pd.isna(row["high"]) else None
                            ),
                            "low": (
                                float(row["low"]) if not pd.isna(row["low"]) else None
                            ),
                            "open": (
                                float(row["open"]) if not pd.isna(row["open"]) else None
                            ),
                            "close": (
                                float(row["close"])
                                if not pd.isna(row["close"])
                                else None
                            ),
                        }
                    )

                return {
                    "ticker": ticker,
                    "prices": prices,
                    "source": "openbb_yfinance",
                    "interval": "1H",
                }

            except Exception as api_error:
                logger.error(f"OpenBB yfinance error for {ticker}: {api_error}")
                raise

        except ImportError:
            logger.error(
                "openbb package not installed. Install with: pip install openbb"
            )
            raise
        except Exception as e:
            logger.error(f"Error fetching price data for {ticker}: {e}")
            raise


def _convert_to_yahoo_ticker(ticker: str) -> str:
    """Convert ticker to Yahoo Finance format for Oslo Stock Exchange."""
    # Yahoo Finance uses .OL suffix for Oslo Stock Exchange
    if not ticker.endswith(".OL") and len(ticker) <= 5:
        return f"{ticker}.OL"
    return ticker


def _get_mock_price_data(
    ticker: str, start_date: datetime, end_date: datetime
) -> Dict[str, Any]:
    """Generate mock price data for development/testing."""
    import random

    # Generate hourly data points
    current_time = start_date
    prices = []

    # Base price around 100-500 NOK for Norwegian stocks
    base_price = random.uniform(100, 500)

    while current_time <= end_date:
        # Simulate price movement
        change_percent = random.uniform(-0.02, 0.02)  # -2% to +2% change
        price = base_price * (1 + change_percent)

        prices.append(
            {
                "timestamp": current_time,
                "price": round(price, 2),
                "volume": random.randint(1000, 10000),
                "high": round(price * (1 + random.uniform(0, 0.01)), 2),
                "low": round(price * (1 - random.uniform(0, 0.01)), 2),
                "open": round(price * (1 + random.uniform(-0.005, 0.005)), 2),
                "close": round(price, 2),
            }
        )

        current_time += timedelta(hours=1)
        base_price = price  # Use current price as base for next iteration

    return {
        "ticker": ticker,
        "prices": prices,
        "source": "mock_yahoo_finance",
        "interval": "1H",
    }


class OpenBBYahooFinancePriceFetcher:
    """Fetcher for OpenBB Yahoo Finance price data with rate limiting and database storage."""

    def __init__(self, db_url: str):
        """Initialize with database connection."""
        self.db_url = db_url
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        # Create tables if they don't exist
        from db.models import Base

        Base.metadata.create_all(self.engine)
        self.markets_config = load_markets_config()
        self.oslo_tz = pytz.timezone("Europe/Oslo")
        self.utc_tz = pytz.UTC

    def _normalize_price_data(self, price_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Normalize OpenBB price data to our schema."""
        normalized_prices = []

        for price_point in price_data.get("prices", []):
            # Handle different timestamp formats
            timestamp = price_point.get("timestamp")
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            elif not isinstance(timestamp, datetime):
                logger.warning(f"Invalid timestamp format: {timestamp}")
                continue

            # Convert to UTC if not already
            if timestamp.tzinfo is None:
                timestamp = self.utc_tz.localize(timestamp)
            else:
                timestamp = timestamp.astimezone(self.utc_tz)

            normalized_price = {
                "ticker": price_data["ticker"],
                "timestamp": timestamp,
                "price": float(price_point.get("price", price_point.get("close", 0))),
                "volume": price_point.get("volume"),
                "high": price_point.get("high"),
                "low": price_point.get("low"),
                "open_price": price_point.get("open"),
                "close_price": price_point.get("close", price_point.get("price")),
                "source": price_data.get("source", "openbb"),
                "interval": price_data.get("interval", "1H"),
            }

            normalized_prices.append(normalized_price)

        return normalized_prices

    def _upsert_price_data(self, session, price_data: Dict[str, Any]) -> int:
        """Upsert price data, returning number of records inserted/updated."""
        inserted_count = 0

        try:
            normalized_prices = self._normalize_price_data(price_data)

            for price_point in normalized_prices:
                try:
                    # Check for existing price data
                    existing = session.execute(
                        select(MarketPrice).where(
                            MarketPrice.ticker == price_point["ticker"],
                            MarketPrice.timestamp == price_point["timestamp"],
                            MarketPrice.interval == price_point["interval"],
                        )
                    ).scalar_one_or_none()

                    if existing:
                        # Update existing record if price changed
                        updated = False
                        for key, value in price_point.items():
                            if (
                                key not in ["id", "created_at"]
                                and getattr(existing, key) != value
                            ):
                                setattr(existing, key, value)
                                updated = True

                        if updated:
                            logger.debug(
                                f"Updated price data for {price_point['ticker']} at {price_point['timestamp']}"
                            )
                            inserted_count += 1
                    else:
                        # Insert new price record
                        market_price = MarketPrice(**price_point)
                        session.add(market_price)
                        session.commit()
                        logger.debug(
                            f"Inserted new price data for {price_point['ticker']} at {price_point['timestamp']}"
                        )
                        inserted_count += 1

                except IntegrityError:
                    session.rollback()
                    logger.debug(
                        f"Duplicate price data skipped for {price_point['ticker']} at {price_point['timestamp']}"
                    )
                except Exception as e:
                    session.rollback()
                    logger.error(f"Error upserting price data: {e}")

        except Exception as e:
            session.rollback()
            logger.error(f"Error processing price data batch: {e}")

        return inserted_count

    def get_latest_price_timestamp(self, ticker: str) -> Optional[datetime]:
        """Get the latest price timestamp for a ticker to avoid duplicates."""
        try:
            with self.SessionLocal() as session:
                result = session.execute(
                    select(func.max(MarketPrice.timestamp)).where(
                        MarketPrice.ticker == ticker, MarketPrice.interval == "1H"
                    )
                ).scalar_one_or_none()

                return result
        except Exception as e:
            logger.error(f"Error getting latest price timestamp for {ticker}: {e}")
            return None

    async def fetch_prices_for_ticker(
        self, ticker: str, days_back: int = 1, force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Fetch price data for a specific ticker."""
        try:
            end_date = datetime.now(self.utc_tz)
            start_date = end_date - timedelta(days=days_back)

            # If not forcing refresh, start from the latest available data
            if not force_refresh:
                latest_timestamp = self.get_latest_price_timestamp(ticker)
                if latest_timestamp:
                    start_date = max(start_date, latest_timestamp + timedelta(hours=1))

            # Skip if we already have recent data
            if start_date >= end_date:
                logger.debug(f"Skipping {ticker} - already have recent data")
                return None

            price_data = await _fetch_price_with_retry(ticker, start_date, end_date)

            if price_data:
                logger.info(
                    f"Fetched {len(price_data.get('prices', []))} price points for {ticker}"
                )
                return price_data
            else:
                logger.warning(f"No price data fetched for {ticker}")
                return None

        except Exception as e:
            logger.error(f"Error fetching prices for {ticker}: {e}")
            return None

    def store_price_data(self, price_data: Dict[str, Any]) -> int:
        """Store price data in the database."""
        if not price_data:
            return 0

        stored_count = 0

        with self.SessionLocal() as session:
            stored_count = self._upsert_price_data(session, price_data)

        return stored_count

    async def fetch_and_store_prices_for_ticker(
        self, ticker: str, days_back: int = 1, force_refresh: bool = False
    ) -> int:
        """Fetch and store price data for a specific ticker."""
        price_data = await self.fetch_prices_for_ticker(
            ticker, days_back, force_refresh
        )

        if price_data:
            return self.store_price_data(price_data)

        return 0

    async def fetch_and_store_all_tickers(
        self, days_back: int = 1, force_refresh: bool = False
    ) -> Dict[str, int]:
        """Fetch and store price data for all Scandinavian tickers."""
        results = {}

        # Get all tickers from market config
        tickers = []
        for market_data in self.markets_config.get("markets", {}).values():
            if "ticker" in market_data:
                tickers.append(market_data["ticker"])

        logger.info(f"Fetching price data for {len(tickers)} tickers")

        # Fetch price data for all tickers concurrently
        tasks = [
            self.fetch_prices_for_ticker(ticker, days_back, force_refresh)
            for ticker in tickers
        ]
        price_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and store
        for ticker, price_result in zip(tickers, price_results):
            if isinstance(price_result, Exception):
                logger.error(f"Failed to fetch price data for {ticker}: {price_result}")
                results[ticker] = 0
            elif price_result:
                stored_count = self.store_price_data(price_result)
                results[ticker] = stored_count
                logger.info(f"Stored {stored_count} price points for {ticker}")
            else:
                results[ticker] = 0

        total_stored = sum(results.values())
        logger.info(f"Total price data points stored: {total_stored}")

        return results


@lru_cache(maxsize=100)
def load_markets_config():
    """Load markets configuration with caching."""
    import os

    import yaml

    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "markets.yml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


async def fetch_openbb_prices(
    db_url: str,
    tickers: Optional[List[str]] = None,
    days_back: int = 1,
    force_refresh: bool = False,
) -> Dict[str, int]:
    """
    Main function to fetch OpenBB Yahoo Finance price data.

    Args:
        db_url: Database connection URL
        tickers: Optional list of tickers to fetch (default: all from config)
        days_back: Number of days back to fetch data
        force_refresh: Whether to refresh existing data

    Returns:
        Dictionary mapping tickers to number of data points stored
    """
    fetcher = OpenBBYahooFinancePriceFetcher(db_url)

    if tickers:
        # Fetch specific tickers
        tasks = [
            fetcher.fetch_and_store_prices_for_ticker(ticker, days_back, force_refresh)
            for ticker in tickers
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        stored_results = {}
        for ticker, result in zip(tickers, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch price data for {ticker}: {result}")
                stored_results[ticker] = 0
            else:
                stored_results[ticker] = result

        return stored_results
    else:
        # Fetch all tickers from config
        return await fetcher.fetch_and_store_all_tickers(days_back, force_refresh)


async def fetch_market_prices_async(
    db_url: str,
    tickers: Optional[List[str]] = None,
    days_back: int = 1,
    force_refresh: bool = False,
    fallback_to_mock: bool = False,
) -> Dict[str, int]:
    """
    Async version of fetch_market_prices - use this when already in an async context.

    Args:
        db_url: Database connection URL
        tickers: Optional list of tickers to fetch
        days_back: Number of days of historical data to fetch
        force_refresh: Whether to refresh existing data
        fallback_to_mock: Whether to use mock data if API fails (for development)

    Returns:
        Dictionary mapping tickers to number of data points stored
    """
    try:
        # Try to import and use OpenBB
        return await fetch_openbb_prices(db_url, tickers, days_back, force_refresh)

    except ImportError as e:
        if fallback_to_mock:
            logger.warning(f"OpenBB not available, using mock data: {e}")
            return _fetch_mock_prices(db_url, tickers, days_back)
        else:
            raise ImportError("OpenBB not installed. Install with: pip install openbb")

    except Exception as e:
        if fallback_to_mock:
            logger.warning(f"OpenBB API failed, using mock data: {e}")
            return _fetch_mock_prices(db_url, tickers, days_back)
        else:
            raise e


def fetch_market_prices(
    db_url: str,
    tickers: Optional[List[str]] = None,
    days_back: int = 1,
    force_refresh: bool = False,
    fallback_to_mock: bool = False,
) -> Dict[str, int]:
    """
    Fetch market price data with optional mock fallback for development.

    Args:
        db_url: Database connection URL
        tickers: Optional list of tickers to fetch
        days_back: Number of days of historical data to fetch
        force_refresh: Whether to refresh existing data
        fallback_to_mock: Whether to use mock data if API fails (for development)

    Returns:
        Dictionary mapping tickers to number of data points stored
    """
    try:
        # Check if we're already in an event loop
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context - this shouldn't happen since this is a sync function
            # But if it does, we need to handle it properly
            raise RuntimeError(
                "fetch_market_prices called from async context - use fetch_market_prices_async instead"
            )
        except RuntimeError:
            # No running event loop, we can use asyncio.run
            import asyncio

            return asyncio.run(
                fetch_openbb_prices(db_url, tickers, days_back, force_refresh)
            )

    except ImportError as e:
        if fallback_to_mock:
            logger.warning(f"OpenBB not available, using mock data: {e}")
            return _fetch_mock_prices(db_url, tickers, days_back)
        else:
            raise ImportError("OpenBB not installed. Install with: pip install openbb")

    except Exception as e:
        if fallback_to_mock:
            logger.warning(f"OpenBB API failed, using mock data: {e}")
            return _fetch_mock_prices(db_url, tickers, days_back)
        else:
            raise e


def _fetch_mock_prices(
    db_url: str, tickers: Optional[List[str]], days_back: int
) -> Dict[str, int]:
    """Fetch mock price data for development/testing."""
    from sqlalchemy import create_engine, func, select
    from sqlalchemy.orm import sessionmaker

    from db.models import Base

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    # Use market config or provided tickers
    if not tickers:
        from config import load_markets_config

        config = load_markets_config()
        tickers = []
        for market_data in config.get("markets", {}).values():
            if "ticker" in market_data:
                tickers.append(market_data["ticker"])

    results = {}
    for ticker in tickers:
        try:
            # Generate and store mock data
            mock_data = _get_mock_price_data(
                ticker, datetime.now() - timedelta(days=days_back), datetime.now()
            )

            with SessionLocal() as session:
                count = 0
                for price_point in mock_data.get("prices", []):
                    # Check if exists
                    existing = session.execute(
                        select(MarketPrice).where(
                            MarketPrice.ticker == ticker,
                            MarketPrice.timestamp == price_point["timestamp"],
                            MarketPrice.interval == "1H",
                        )
                    ).scalar_one_or_none()

                    if not existing:
                        market_price = MarketPrice(
                            ticker=ticker,
                            timestamp=price_point["timestamp"],
                            price=price_point["price"],
                            volume=price_point.get("volume"),
                            high=price_point.get("high"),
                            low=price_point.get("low"),
                            open_price=price_point.get("open"),
                            close_price=price_point.get("close"),
                            source="mock_openbb",
                            interval="1H",
                        )
                        session.add(market_price)
                        session.commit()
                        count += 1

            results[ticker] = count
            logger.info(f"Stored {count} mock price points for {ticker}")

        except Exception as e:
            logger.error(f"Failed to generate mock data for {ticker}: {e}")
            results[ticker] = 0

    return results
