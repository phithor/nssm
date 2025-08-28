"""
Abstract base class for forum scrapers

Provides common functionality for all forum scrapers including
session management, user agent handling, and basic HTTP operations.
"""

import abc
import logging
from abc import ABCMeta
from typing import Any, List, Optional
from urllib.parse import urljoin

import requests

from db.models import Post

logger = logging.getLogger(__name__)


class Scraper(metaclass=ABCMeta):
    """
    Abstract base class for forum scrapers.

    All scrapers must implement fetch() and parse() methods.
    Provides common functionality like session management and error handling.
    """

    def __init__(self, base_url: str, user_agent: Optional[str] = None):
        """
        Initialize the scraper with base configuration.

        Args:
            base_url: Base URL for the forum
            user_agent: Custom user agent string (optional)
        """
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent or self._get_default_user_agent()
        self.session = self._create_session()

        # Configure logging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _get_default_user_agent(self) -> str:
        """Get a default user agent string."""
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )

    def _create_session(self) -> requests.Session:
        """Create and configure a requests session."""
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "image/webp,*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )
        return session

    @abc.abstractmethod
    def fetch(self, url: str, **kwargs: Any) -> Optional[str]:
        """
        Fetch content from the given URL.

        Args:
            url: URL to fetch (can be relative or absolute)
            **kwargs: Additional arguments for the request

        Returns:
            HTML content as string, or None if failed
        """
        pass

    @abc.abstractmethod
    def parse(self, html: str) -> List[Post]:
        """
        Parse HTML content and extract forum posts.

        Args:
            html: HTML content to parse

        Returns:
            List of Post objects extracted from the HTML
        """
        pass

    def get_full_url(self, path: str) -> str:
        """Convert relative path to full URL."""
        if path.startswith("http"):
            return path
        return urljoin(self.base_url, path.lstrip("/"))

    def close(self):
        """Close the session and clean up resources."""
        if self.session:
            self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
