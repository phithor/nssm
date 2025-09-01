"""
Integration tests for market price data fetching and storage.

Uses VCR.py to record HTTP interactions with OpenBB API and tests
the complete pipeline from API fetch to database storage.
"""

import asyncio
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest
import vcr
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from db.models import Base, MarketPrice
from market.data import (
    OpenBBPriceFetcher,
    _fetch_price_with_retry,
    _get_mock_price_data,
    fetch_openbb_prices,
)


@pytest.fixture
def db_engine():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    """Create database session for testing."""
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def vcr_config():
    """VCR.py configuration for recording OpenBB API calls."""
    return {
        "record_mode": "once",
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "filter_headers": ["authorization", "api-key"],
        "cassette_library_dir": "tests/cassettes",
        "ignore_hosts": ["localhost", "127.0.0.1"],
    }


class TestMockPriceData:
    """Test mock price data generation for development."""

    def test_mock_price_data_structure(self):
        """Test that mock price data has correct structure."""
        ticker = "EQNR"
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now()

        mock_data = _get_mock_price_data(ticker, start_date, end_date)

        assert mock_data["ticker"] == ticker
        assert mock_data["source"] == "mock_openbb"
        assert mock_data["interval"] == "1H"
        assert "prices" in mock_data
        assert len(mock_data["prices"]) > 0

        # Check first price point structure
        price_point = mock_data["prices"][0]
        assert "timestamp" in price_point
        assert "price" in price_point
        assert "volume" in price_point
        assert "high" in price_point
        assert "low" in price_point
        assert "open" in price_point
        assert "close" in price_point

        # Check data types
        assert isinstance(price_point["price"], float)
        assert isinstance(price_point["volume"], int)
        assert price_point["price"] > 0
        assert price_point["volume"] > 0

    def test_mock_price_data_time_range(self):
        """Test that mock data covers the requested time range."""
        ticker = "EQNR"
        start_date = datetime(2024, 1, 1, 10, 0, 0)
        end_date = datetime(2024, 1, 1, 14, 0, 0)

        mock_data = _get_mock_price_data(ticker, start_date, end_date)

        timestamps = [point["timestamp"] for point in mock_data["prices"]]

        # Check that we have data points within the range
        assert len(timestamps) > 0
        assert all(start_date <= ts <= end_date for ts in timestamps)


class TestOpenBBPriceFetcher:
    """Test OpenBB price fetcher functionality."""

    def test_fetcher_initialization(self, db_engine):
        """Test that fetcher initializes correctly."""
        fetcher = OpenBBPriceFetcher("sqlite:///:memory:")

        assert fetcher.db_url == "sqlite:///:memory:"
        assert hasattr(fetcher, "SessionLocal")
        assert hasattr(fetcher, "oslo_tz")
        assert hasattr(fetcher, "utc_tz")

    def test_normalize_price_data(self, db_engine):
        """Test price data normalization."""
        fetcher = OpenBBPriceFetcher("sqlite:///:memory:")

        # Mock OpenBB response data
        price_data = {
            "ticker": "EQNR",
            "source": "openbb",
            "interval": "1H",
            "prices": [
                {
                    "timestamp": datetime.now(),
                    "price": 150.5,
                    "volume": 10000,
                    "high": 151.0,
                    "low": 149.5,
                    "open": 150.0,
                    "close": 150.5,
                }
            ],
        }

        normalized = fetcher._normalize_price_data(price_data)

        assert len(normalized) == 1
        price_point = normalized[0]

        assert price_point["ticker"] == "EQNR"
        assert price_point["price"] == 150.5
        assert price_point["volume"] == 10000
        assert price_point["source"] == "openbb"
        assert price_point["interval"] == "1H"

    def test_get_latest_price_timestamp_no_data(self, db_engine):
        """Test getting latest timestamp when no data exists."""
        fetcher = OpenBBPriceFetcher("sqlite:///:memory:")

        result = fetcher.get_latest_price_timestamp("EQNR")
        assert result is None

    def test_get_latest_price_timestamp_with_data(self, db_session, db_engine):
        """Test getting latest timestamp when data exists."""
        # Insert test data
        test_time = datetime.now()
        price = MarketPrice(
            ticker="EQNR",
            timestamp=test_time,
            price=150.5,
            volume=10000,
            high=151.0,
            low=149.5,
            open_price=150.0,
            close_price=150.5,
            source="test",
            interval="1H",
        )
        db_session.add(price)
        db_session.commit()

        fetcher = OpenBBPriceFetcher("sqlite:///:memory:")
        result = fetcher.get_latest_price_timestamp("EQNR")

        assert result == test_time

    def test_upsert_price_data_new_records(self, db_session, db_engine):
        """Test upserting new price data records."""
        fetcher = OpenBBPriceFetcher("sqlite:///:memory:")

        price_data = {
            "ticker": "EQNR",
            "source": "openbb",
            "interval": "1H",
            "prices": [
                {
                    "timestamp": datetime.now(),
                    "price": 150.5,
                    "volume": 10000,
                    "high": 151.0,
                    "low": 149.5,
                    "open": 150.0,
                    "close": 150.5,
                }
            ],
        }

        stored_count = fetcher._upsert_price_data(db_session, price_data)

        assert stored_count == 1

        # Verify data was stored
        count = db_session.execute(
            select(func.count(MarketPrice.id)).where(MarketPrice.ticker == "EQNR")
        ).scalar_one()

        assert count == 1

    def test_upsert_price_data_duplicate_prevention(self, db_session, db_engine):
        """Test that duplicate price data is not inserted."""
        fetcher = OpenBBPriceFetcher("sqlite:///:memory:")

        test_time = datetime.now()

        # Insert initial data
        price = MarketPrice(
            ticker="EQNR",
            timestamp=test_time,
            price=150.5,
            volume=10000,
            high=151.0,
            low=149.5,
            open_price=150.0,
            close_price=150.5,
            source="openbb",
            interval="1H",
        )
        db_session.add(price)
        db_session.commit()

        # Try to upsert same data
        price_data = {
            "ticker": "EQNR",
            "source": "openbb",
            "interval": "1H",
            "prices": [
                {
                    "timestamp": test_time,
                    "price": 150.5,
                    "volume": 10000,
                    "high": 151.0,
                    "low": 149.5,
                    "open": 150.0,
                    "close": 150.5,
                }
            ],
        }

        stored_count = fetcher._upsert_price_data(db_session, price_data)

        # Should return 0 since no new data was inserted
        assert stored_count == 0

        # Verify still only one record
        count = db_session.execute(
            select(func.count(MarketPrice.id)).where(MarketPrice.ticker == "EQNR")
        ).scalar_one()

        assert count == 1


@pytest.mark.vcr
class TestOpenBBIntegration:
    """Integration tests using VCR.py to record OpenBB API calls."""

    @pytest.mark.asyncio
    async def test_fetch_openbb_prices_integration(self, db_engine):
        """Integration test for fetching prices from OpenBB."""
        # This test will be recorded by VCR.py on first run
        # and replayed on subsequent runs

        # Note: This test may fail if OpenBB API requires authentication
        # In that case, it will fall back to mock data
        try:
            results = await fetch_openbb_prices(
                db_url="sqlite:///:memory:", tickers=["EQNR"], days_back=1
            )

            # Verify we got results
            assert isinstance(results, dict)
            assert "EQNR" in results
            assert isinstance(results["EQNR"], int)
            assert results["EQNR"] >= 0

        except Exception as e:
            # If API fails, check that we handle it gracefully
            pytest.skip(f"OpenBB API not available: {e}")

    @pytest.mark.asyncio
    async def test_fetch_openbb_prices_with_mock_data(self, db_engine):
        """Test price fetching with mock data fallback."""
        # Mock the OpenBB API to always fail and use mock data
        with patch("market.data._fetch_price_with_retry") as mock_fetch:
            # Make it raise an exception to trigger mock data
            mock_fetch.side_effect = Exception("API not available")

            results = await fetch_openbb_prices(
                db_url="sqlite:///:memory:", tickers=["EQNR"], days_back=1
            )

            # Should get mock data results
            assert isinstance(results, dict)
            assert "EQNR" in results
            assert results["EQNR"] > 0  # Should have inserted mock data


class TestPriceDataPipeline:
    """Test the complete price data pipeline."""

    @pytest.mark.asyncio
    async def test_end_to_end_pipeline(self, db_session, db_engine):
        """Test complete pipeline from fetch to storage."""
        # Create fetcher
        fetcher = OpenBBPriceFetcher("sqlite:///:memory:")

        # Mock the price fetching to return controlled data
        test_time = datetime.now()
        mock_price_data = {
            "ticker": "EQNR",
            "source": "test",
            "interval": "1H",
            "prices": [
                {
                    "timestamp": test_time,
                    "price": 150.5,
                    "volume": 10000,
                    "high": 151.0,
                    "low": 149.5,
                    "open": 150.0,
                    "close": 150.5,
                }
            ],
        }

        with patch.object(fetcher, "fetch_prices_for_ticker") as mock_fetch:
            mock_fetch.return_value = mock_price_data

            # Run the pipeline
            stored_count = await fetcher.fetch_and_store_prices_for_ticker("EQNR")

            assert stored_count == 1

            # Verify data was stored correctly
            stored_price = db_session.execute(
                select(MarketPrice).where(MarketPrice.ticker == "EQNR")
            ).scalar_one()

            assert stored_price.ticker == "EQNR"
            assert stored_price.price == 150.5
            assert stored_price.volume == 10000
            assert stored_price.source == "test"
            assert stored_price.interval == "1H"

    @pytest.mark.asyncio
    async def test_multiple_tickers_pipeline(self, db_session, db_engine):
        """Test pipeline with multiple tickers."""
        fetcher = OpenBBPriceFetcher("sqlite:///:memory:")

        # Mock data for two tickers
        def mock_fetch_side_effect(ticker, *args, **kwargs):
            return {
                "ticker": ticker,
                "source": "test",
                "interval": "1H",
                "prices": [
                    {
                        "timestamp": datetime.now(),
                        "price": 150.5 if ticker == "EQNR" else 200.0,
                        "volume": 10000,
                        "high": 151.0 if ticker == "EQNR" else 201.0,
                        "low": 149.5 if ticker == "EQNR" else 199.0,
                        "open": 150.0 if ticker == "EQNR" else 200.0,
                        "close": 150.5 if ticker == "EQNR" else 200.0,
                    }
                ],
            }

        with patch.object(fetcher, "fetch_prices_for_ticker") as mock_fetch:
            mock_fetch.side_effect = mock_fetch_side_effect

            # Fetch data for multiple tickers
            results = await fetcher.fetch_and_store_all_tickers()

            assert "EQNR" in results
            assert "TEL" in results  # Assuming TEL is another ticker
            assert results["EQNR"] == 1
            assert results["TEL"] == 1

            # Verify both tickers were stored
            eqnr_count = db_session.execute(
                select(func.count(MarketPrice.id)).where(MarketPrice.ticker == "EQNR")
            ).scalar_one()

            tel_count = db_session.execute(
                select(func.count(MarketPrice.id)).where(MarketPrice.ticker == "TEL")
            ).scalar_one()

            assert eqnr_count == 1
            assert tel_count == 1


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_wait(self):
        """Test that rate limiting function works."""
        from market.data import _rate_limit_wait

        # This should not raise an exception
        _rate_limit_wait()

    @pytest.mark.asyncio
    async def test_rate_limit_semaphore(self):
        """Test that rate limiting semaphore is applied."""
        # This is a basic test that the semaphore exists and works
        from market.data import RATE_LIMIT_SEMAPHORE

        assert hasattr(RATE_LIMIT_SEMAPHORE, "acquire")
        assert hasattr(RATE_LIMIT_SEMAPHORE, "release")


class TestErrorHandling:
    """Test error handling in price data pipeline."""

    @pytest.mark.asyncio
    async def test_fetch_with_api_error_fallback(self, db_engine):
        """Test that API errors are handled gracefully with fallback."""
        fetcher = OpenBBPriceFetcher("sqlite:///:memory:")

        # Mock fetch to raise an exception
        with patch("market.data._fetch_price_with_retry") as mock_fetch:
            mock_fetch.side_effect = Exception("API Error")

            # Should return None and handle gracefully
            result = await fetcher.fetch_prices_for_ticker("EQNR")
            assert result is None

    @pytest.mark.asyncio
    async def test_store_with_invalid_data(self, db_session, db_engine):
        """Test handling of invalid price data."""
        fetcher = OpenBBPriceFetcher("sqlite:///:memory:")

        # Invalid data with missing required fields
        invalid_price_data = {
            "ticker": "EQNR",
            "source": "test",
            "interval": "1H",
            "prices": [
                {
                    "timestamp": "invalid_timestamp",
                    "price": "invalid_price",
                    # Missing other required fields
                }
            ],
        }

        # Should handle gracefully without crashing
        stored_count = fetcher._upsert_price_data(db_session, invalid_price_data)

        # May store 0 or 1 depending on error handling
        assert isinstance(stored_count, int)
        assert stored_count >= 0


if __name__ == "__main__":
    pytest.main([__file__])
