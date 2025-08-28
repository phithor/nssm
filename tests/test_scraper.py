"""
Unit and integration tests for the forum scraper system.

Tests all components including base classes, utilities, scrapers,
and the persistence layer.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from scraper.avanza import AvanzaScraper
from scraper.base import Scraper
from scraper.hegnar import HegnarScraper
from scraper.persistence import ScraperPersistence
from scraper.utils import polite_delay, randomize_headers


class TestScraperBase:
    """Test the base Scraper class."""

    def test_scraper_initialization(self):
        """Test scraper initialization with base URL."""
        scraper = MockScraper("https://example.com")
        assert scraper.base_url == "https://example.com"
        assert scraper.user_agent is not None
        assert scraper.session is not None

    def test_get_full_url(self):
        """Test URL construction from relative paths."""
        scraper = MockScraper("https://example.com")
        assert scraper.get_full_url("/path") == "https://example.com/path"
        assert scraper.get_full_url("https://other.com") == "https://other.com"

    def test_context_manager(self):
        """Test context manager functionality."""
        with MockScraper("https://example.com") as scraper:
            assert scraper.session is not None
        # Session should be closed after context exit


class TestDelayUtils:
    """Test delay utility functions."""

    def test_polite_delay(self):
        """Test polite delay function."""
        start_time = datetime.now()
        polite_delay(0.1, 0.1)  # Very short delay for testing
        end_time = datetime.now()
        assert (end_time - start_time).total_seconds() >= 0.1


class TestHeaderUtils:
    """Test header utility functions."""

    def test_randomize_headers(self):
        """Test header randomization."""
        headers = randomize_headers()
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Accept-Language" in headers


class TestHegnarScraper:
    """Test Hegnar/Finansavisen scraper."""

    def test_hegnar_scraper_initialization(self):
        """Test Hegnar scraper initialization."""
        scraper = HegnarScraper()
        assert scraper.base_url == "https://www.finansavisen.no"

    @patch("scraper.hegnar.check_robots_txt")
    @patch("scraper.hegnar.polite_delay")
    def test_fetch_method(self, mock_delay, mock_robots):
        """Test fetch method with mocked dependencies."""
        mock_robots.return_value = True
        scraper = HegnarScraper()
        # Mock the session response
        with patch.object(scraper.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.text = "<html>test</html>"
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            result = scraper.fetch("https://example.com")
            assert result == "<html>test</html>"


class TestAvanzaScraper:
    """Test Avanza/Placera scraper."""

    def test_avanza_scraper_initialization(self):
        """Test Avanza scraper initialization."""
        scraper = AvanzaScraper()
        assert scraper.base_url == "https://www.avanza.se"

    @patch("scraper.avanza.check_robots_txt")
    @patch("scraper.avanza.polite_delay")
    def test_fetch_method(self, mock_delay, mock_robots):
        """Test fetch method with mocked dependencies."""
        mock_robots.return_value = True
        scraper = AvanzaScraper()
        # Mock the session response
        with patch.object(scraper.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.text = "<html>test</html>"
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            result = scraper.fetch("https://example.com")
            assert result == "<html>test</html>"


class TestScraperPersistence:
    """Test the persistence layer."""

    def test_persistence_initialization(self):
        """Test persistence layer initialization."""
        persistence = ScraperPersistence()
        assert persistence.hegnar_scraper is not None
        assert persistence.avanza_scraper is not None


class MockScraper(Scraper):
    """Mock scraper for testing base class functionality."""

    def fetch(self, url: str, **kwargs):
        """Mock fetch implementation."""
        return "<html>test</html>"

    def parse(self, html: str):
        """Mock parse implementation."""
        return []


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )


def pytest_collection_modifyitems(config, items):
    """Add slow marker to selenium tests."""
    for item in items:
        if "test_selenium" in item.nodeid:
            item.add_marker(pytest.mark.slow)
