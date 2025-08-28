"""
Avanza Forum Scraper with Selenium Fallback

Scrapes posts from Avanza Forum (https://www.avanza.se) using requests+BeautifulSoup
with automatic fallback to Selenium when JavaScript rendering is required.
"""

import logging
import re
from datetime import datetime
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from db.models import Post

from .base import Scraper
from .utils.delay import polite_delay
from .utils.headers import randomize_headers
from .utils.robots import check_robots_txt
from .utils.selenium_wrapper import SeleniumWrapper


class AvanzaScraper(Scraper):
    """
    Scraper for Avanza Forum with Selenium fallback.

    Avanza is a Swedish financial services company with active forums
    for stock discussions. Some content requires JavaScript rendering.
    """

    def __init__(self, use_selenium_fallback: bool = True):
        """
        Initialize Avanza scraper with configuration.

        Args:
            use_selenium_fallback: Whether to use Selenium as fallback
        """
        super().__init__(
            base_url="https://www.avanza.se",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.use_selenium_fallback = use_selenium_fallback

        # Ticker regex pattern for Swedish stocks
        self.ticker_pattern = re.compile(r"\b[A-Z]{2,4}\b")

        # Forum-specific selectors for Avanza
        self.selectors = {
            "post_container": ".forum-post, .post, .message, .thread-post",
            "author": ".author, .username, .user, .poster",
            "timestamp": ".timestamp, .date, .time, .post-date",
            "content": ".content, .message-text, .post-text, .post-content",
            "pagination": ".pagination, .pages, .page-nav",
        }

        # Initialize Selenium wrapper if fallback is enabled
        self.selenium_wrapper = None
        if self.use_selenium_fallback:
            self.selenium_wrapper = SeleniumWrapper(headless=True)

    def fetch(self, url: str, **kwargs) -> Optional[str]:
        """
        Fetch content from Avanza forum pages with automatic fallback.

        Args:
            url: URL to fetch
            **kwargs: Additional request parameters

        Returns:
            HTML content as string, or None if failed
        """
        # First try with requests+BeautifulSoup
        html = self._fetch_with_requests(url, **kwargs)

        # Check if content appears to be JavaScript-rendered
        if html and self._needs_javascript_fallback(html):
            self.logger.info(
                f"Content appears to be JavaScript-rendered, "
                f"trying Selenium fallback for {url}"
            )
            html = self._fetch_with_selenium(url)

        return html

    def _fetch_with_requests(self, url: str, **kwargs) -> Optional[str]:
        """Fetch content using requests library."""
        try:
            # Check robots.txt compliance
            if not check_robots_txt(url, self.user_agent):
                self.logger.warning(f"Robots.txt disallows access to {url}")
                return None

            # Randomize headers for this request
            headers = randomize_headers()
            self.session.headers.update(headers)

            # Make the request
            response = self.session.get(url, timeout=30, **kwargs)
            response.raise_for_status()

            # Implement polite delay
            polite_delay()

            self.logger.info(f"Successfully fetched {url} with requests")
            return response.text

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed for {url}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error fetching {url}: {e}")
            return None

    def _fetch_with_selenium(self, url: str) -> Optional[str]:
        """Fetch content using Selenium WebDriver."""
        if not self.selenium_wrapper:
            self.logger.warning("Selenium fallback not available")
            return None

        try:
            html = self.selenium_wrapper.get_page_source(url)
            if html:
                self.logger.info(f"Successfully fetched {url} with Selenium")
            return html
        except Exception as e:
            self.logger.error(f"Selenium fetch failed for {url}: {e}")
            return None

    def _needs_javascript_fallback(self, html: str) -> bool:
        """
        Detect if content requires JavaScript rendering.

        Args:
            html: HTML content to analyze

        Returns:
            True if JavaScript fallback is needed
        """
        # Common indicators that content is JavaScript-rendered
        js_indicators = [
            "Loading...",
            "Please wait...",
            "JavaScript is required",
            "noscript",
            "data-reactroot",
            "ng-app",
            "v-app",
            "x-data",
            "loading",
            "spinner",
            "skeleton",
        ]

        html_lower = html.lower()
        for indicator in js_indicators:
            if indicator.lower() in html_lower:
                return True

        # Check if content appears to be minimal/empty
        soup = BeautifulSoup(html, "html.parser")
        text_content = soup.get_text(strip=True)

        # If text content is very short, might be JavaScript-rendered
        if len(text_content) < 100:
            return True

        # Check for common forum content patterns
        post_containers = soup.select(self.selectors["post_container"])
        if not post_containers:
            return True

        return False

    def parse(self, html: str) -> List[Post]:
        """
        Parse HTML content and extract forum posts.

        Args:
            html: HTML content to parse

        Returns:
            List of Post objects extracted from the HTML
        """
        posts = []

        try:
            soup = BeautifulSoup(html, "html.parser")

            # Find all post containers
            post_containers = soup.select(self.selectors["post_container"])

            if not post_containers:
                self.logger.warning(
                    "No post containers found. Selectors may need adjustment."
                )
                # Try alternative selectors
                post_containers = soup.find_all(
                    ["div", "article"],
                    class_=re.compile(r"post|message|comment|thread"),
                )

            self.logger.info(f"Found {len(post_containers)} post containers")

            for container in post_containers:
                try:
                    post = self._extract_post(container)
                    if post:
                        posts.append(post)
                except Exception as e:
                    self.logger.error(f"Error extracting post from container: {e}")
                    continue

            self.logger.info(f"Successfully extracted {len(posts)} posts")

        except Exception as e:
            self.logger.error(f"Error parsing HTML: {e}")

        return posts

    def _extract_post(self, container) -> Optional[Post]:
        """
        Extract a single post from a container element.

        Args:
            container: BeautifulSoup element containing post data

        Returns:
            Post object or None if extraction failed
        """
        try:
            # Extract author
            author_elem = container.select_one(self.selectors["author"])
            author = author_elem.get_text(strip=True) if author_elem else "Unknown"

            # Extract timestamp
            timestamp_elem = container.select_one(self.selectors["timestamp"])
            timestamp = (
                self._parse_timestamp(timestamp_elem)
                if timestamp_elem
                else datetime.now()
            )

            # Extract content
            content_elem = container.select_one(self.selectors["content"])
            if not content_elem:
                return None

            raw_text = content_elem.get_text(strip=True)
            if not raw_text:
                return None

            # Extract ticker symbols
            tickers = self._extract_tickers(raw_text)
            if not tickers:
                # Skip posts without ticker mentions
                return None

            # Use the first ticker found (could be enhanced to handle multiple)
            ticker = tickers[0]

            # Create post object
            post = Post(
                forum_id=None,  # Will be set by persistence layer
                author=author or "Anonymous",
                raw_text=raw_text,
                clean_text=raw_text,  # For now, same as raw_text
                timestamp=timestamp or datetime.now(),
                ticker=ticker,
                url=None,  # No direct URL for individual posts in this scraper
                post_id=None,  # No direct post ID for individual posts in this scraper
                metadata={
                    "source": "avanza_forum",
                    "container_class": container.get("class", []),
                },
            )

            return post

        except Exception as e:
            self.logger.error(f"Error extracting post data: {e}")
            return None

    def _extract_tickers(self, text: str) -> List[str]:
        """
        Extract ticker symbols from text using regex pattern.

        Args:
            text: Text to search for tickers

        Returns:
            List of found ticker symbols
        """
        tickers = self.ticker_pattern.findall(text.upper())

        # Filter out common non-ticker words
        common_words = {
            "THE",
            "AND",
            "FOR",
            "ARE",
            "YOU",
            "ALL",
            "HER",
            "HIS",
            "ITS",
            "OUR",
            "VAR",
            "OCH",
            "ATT",
        }
        tickers = [ticker for ticker in tickers if ticker not in common_words]

        # Remove duplicates while preserving order
        seen = set()
        unique_tickers = []
        for ticker in tickers:
            if ticker not in seen:
                seen.add(ticker)
                unique_tickers.append(ticker)

        return unique_tickers

    def _parse_timestamp(self, timestamp_elem) -> datetime:
        """
        Parse timestamp from various formats.

        Args:
            timestamp_elem: BeautifulSoup element containing timestamp

        Returns:
            Parsed datetime object
        """
        try:
            timestamp_text = timestamp_elem.get_text(strip=True)

            # Try to parse various timestamp formats
            # Common Swedish date formats
            swedish_formats = [
                "%Y-%m-%d %H:%M:%S",  # 2025-08-27 14:30:00
                "%Y-%m-%d %H:%M",  # 2025-08-27 14:30
                "%Y-%m-%d",  # 2025-08-27
                "%d/%m/%Y %H:%M",  # 27/08/2025 14:30
                "%d/%m/%Y",  # 27/08/2025
                "%d.%m.%Y %H:%M",  # 27.08.2025 14:30
                "%d.%m.%Y",  # 27.08.2025
            ]

            for fmt in swedish_formats:
                try:
                    return datetime.strptime(timestamp_text, fmt)
                except ValueError:
                    continue

            # If all parsing fails, return current time
            self.logger.warning(f"Could not parse timestamp: {timestamp_text}")
            return datetime.now()

        except Exception as e:
            self.logger.error(f"Error parsing timestamp: {e}")
            return datetime.now()

    def scrape_forum_page(self, page_url: str, forum_id: int) -> List[Post]:
        """
        Scrape a specific forum page and return posts with forum_id set.

        Args:
            page_url: URL of the forum page to scrape
            forum_id: Database ID of the forum

        Returns:
            List of Post objects with forum_id set
        """
        html = self.fetch(page_url)
        if not html:
            return []

        posts = self.parse(html)

        # Set forum_id for all posts
        for post in posts:
            post.forum_id = forum_id

        return posts

    def get_forum_posts(self, forum_id: int, max_pages: int = 5) -> List[Post]:
        """
        Scrape multiple forum pages to get comprehensive post data.

        Args:
            forum_id: Database ID of the forum
            max_pages: Maximum number of pages to scrape

        Returns:
            List of all Post objects found
        """
        all_posts = []

        # Start with the main forum page
        base_url = f"{self.base_url}/forum"

        for page in range(1, max_pages + 1):
            if page == 1:
                page_url = base_url
            else:
                page_url = f"{base_url}?page={page}"

            self.logger.info(f"Scraping page {page}: {page_url}")

            posts = self.scrape_forum_page(page_url, forum_id)
            if not posts:
                self.logger.info(f"No posts found on page {page}, stopping")
                break

            all_posts.extend(posts)

            # Polite delay between pages
            if page < max_pages:
                polite_delay()

        self.logger.info(f"Total posts scraped: {len(all_posts)}")
        return all_posts

    def scrape_forum_feed(self, max_posts: int = 50) -> List[Post]:
        """Scrape the main forum feed page"""
        try:
            url = f"{self.base_url}/forum"  # Main forum page
            self.logger.info(f"Scraping forum feed: {url}")

            html = self.fetch(url)
            if html:
                posts = self.parse(html)
                # Limit posts if needed
                if max_posts and len(posts) > max_posts:
                    posts = posts[:max_posts]
                return posts
            else:
                self.logger.warning("Failed to fetch forum feed")
                return []

        except Exception as e:
            self.logger.error(f"Error scraping forum feed: {e}")
            return []

    def close(self):
        """Close resources including Selenium wrapper."""
        super().close()
        if self.selenium_wrapper:
            self.selenium_wrapper.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
