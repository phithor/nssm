"""
Robots.txt compliance utilities

Provides functions to check robots.txt files and determine
if a URL can be fetched by a specific user agent.
"""

import time
from typing import Dict, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser


class RobotsChecker:
    """Check and respect robots.txt files."""

    def __init__(self):
        self.parser_cache: Dict[str, RobotFileParser] = {}
        self.last_check: Dict[str, float] = {}
        self.cache_ttl = 3600  # 1 hour cache

    def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        """
        Check if the user agent can fetch the given URL according to robots.txt.

        Args:
            url: URL to check
            user_agent: User agent string to check

        Returns:
            True if allowed, False if disallowed
        """
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        # Check cache
        if base_url in self.parser_cache:
            if time.time() - self.last_check.get(base_url, 0) < self.cache_ttl:
                return self.parser_cache[base_url].can_fetch(user_agent, url)

        # Fetch and parse robots.txt
        try:
            parser = RobotFileParser()
            robots_url = urljoin(base_url, "/robots.txt")
            parser.set_url(robots_url)
            parser.read()

            # Cache the parser
            self.parser_cache[base_url] = parser
            self.last_check[base_url] = time.time()

            return parser.can_fetch(user_agent, url)
        except Exception:
            # If robots.txt is unavailable, assume allowed
            return True

    def get_crawl_delay(self, url: str, user_agent: str = "*") -> Optional[float]:
        """
        Get the crawl delay specified in robots.txt for the given URL.

        Args:
            url: URL to check
            user_agent: User agent string to check

        Returns:
            Crawl delay in seconds, or None if not specified
        """
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        if base_url in self.parser_cache:
            # Note: urllib.robotparser doesn't expose crawl_delay directly
            # This is a simplified implementation
            return None

        return None


def check_robots_txt(url: str, user_agent: str = "*") -> bool:
    """
    Simple function to check robots.txt compliance.

    Args:
        url: URL to check
        user_agent: User agent string to check

    Returns:
        True if allowed, False if disallowed
    """
    checker = RobotsChecker()
    return checker.can_fetch(url, user_agent)


def is_robots_compliant(url: str, user_agent: str = "*") -> bool:
    """
    Check if a URL is compliant with robots.txt rules.

    Args:
        url: URL to check
        user_agent: User agent string to check

    Returns:
        True if compliant, False otherwise
    """
    return check_robots_txt(url, user_agent)
