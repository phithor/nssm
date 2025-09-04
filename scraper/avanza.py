"""
Placera Forum Scraper for Swedish Financial Forums

Scrapes posts from Placera Forum (https://forum.placera.se)
using requests+BeautifulSoup with automatic fallback to Selenium when
JavaScript rendering is required.
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


class PlaceraScraper(Scraper):
    """
    Scraper for Placera Forum with Selenium fallback.

    Scrapes posts from https://forum.placera.se with automatic detection
    and appropriate selectors for the platform.
    """

    def __init__(self, use_selenium_fallback: bool = True):
        """
        Initialize scraper with configuration.

        Args:
            use_selenium_fallback: Whether to use Selenium as fallback
        """
        super().__init__(
            base_url="https://forum.placera.se",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.use_selenium_fallback = use_selenium_fallback

        # Ticker regex pattern for Swedish stocks
        self.ticker_pattern = re.compile(r"\b[A-Z]{2,4}\b")

        # Placera Forum selectors
        self.selectors = {
            "post_container": "article.post-card",
            "author": "a[data-testid='author-name']",
            "ticker": "a[data-testid='destination-label']",
            "title": "h3",
            "content": "div.post-body",
            "timestamp": "span",
            "pagination": ".pagination, .pages, .page-nav",
        }

        # Initialize Selenium wrapper if fallback is enabled
        self.selenium_wrapper = None
        if self.use_selenium_fallback:
            self.selenium_wrapper = SeleniumWrapper(headless=True)

    def fetch(self, url: str, **kwargs) -> Optional[str]:
        """
        Fetch content from Placera forum pages with automatic fallback.

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

    def parse(self, html: str, url: str = None) -> List[Post]:
        """
        Parse HTML content and extract forum posts.

        Args:
            html: HTML content to parse
            url: URL of the page being parsed (for context)

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

            # Extract ticker/company from destination label
            ticker_elem = container.select_one(self.selectors["ticker"])
            ticker = ticker_elem.get_text(strip=True) if ticker_elem else None

            # Extract title
            title_elem = container.select_one(self.selectors["title"])
            title = title_elem.get_text(strip=True) if title_elem else "No title"

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

            # Use ticker from destination label if available, otherwise extract
            # from text
            if not ticker:
                tickers = self._extract_tickers(raw_text)
                if not tickers:
                    # Skip posts without ticker mentions
                    return None
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
                    "source": "placera_forum",
                    "title": title,
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
                posts = self.parse(html, url)
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

    def extract_sidebar_data(self, html: str) -> dict:
        """
        Extract sidebar data including popular posts, companies, and groups.

        Args:
            html: HTML content to parse

        Returns:
            Dictionary containing sidebar data
        """
        try:
            soup = BeautifulSoup(html, "html.parser")
            sidebar_data = {
                "popular_posts": [],
                "popular_companies": [],
                "popular_groups": [],
                "popular_members": [],
            }

            # Extract popular posts - look for h3 containing "Populära inlägg"
            popular_posts_section = soup.find(
                "h3", string=lambda text: text and "Populära inlägg" in text
            )
            if popular_posts_section:
                # Find the parent container
                container = popular_posts_section.find_parent(
                    "div", class_=lambda x: x and "bg-surface-primary" in x
                )
                if container:
                    post_links = container.find_all(
                        "a", href=lambda href: href and "/inlagg/" in href
                    )
                    for link in post_links:
                        title_elem = link.find("h4")
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            # Look for comment count in the same link
                            comment_text = link.get_text()
                            import re

                            comment_match = re.search(r"(\d+)", comment_text)
                            comment_count = (
                                comment_match.group(1) if comment_match else "0"
                            )
                            sidebar_data["popular_posts"].append(
                                {
                                    "title": title,
                                    "url": link.get("href", ""),
                                    "comment_count": comment_count,
                                }
                            )

            # Extract popular companies - look for h3 containing "Populära bolag"
            popular_companies_section = soup.find(
                "h3", string=lambda text: text and "Populära bolag" in text
            )
            if popular_companies_section:
                container = popular_companies_section.find_parent(
                    "div", class_=lambda x: x and "bg-surface-primary" in x
                )
                if container:
                    company_links = container.find_all(
                        "a", href=lambda href: href and "/bolag/" in href
                    )
                    for link in company_links:
                        name_elem = link.find("h4")
                        if name_elem:
                            name = name_elem.get_text(strip=True)
                            # Look for follower count in the same link
                            follower_text = link.get_text()
                            import re

                            follower_match = re.search(r"(\d+)", follower_text)
                            follower_count = (
                                follower_match.group(1) if follower_match else "0"
                            )
                            sidebar_data["popular_companies"].append(
                                {
                                    "name": name,
                                    "url": link.get("href", ""),
                                    "follower_count": follower_count,
                                }
                            )

            # Extract popular groups - look for h3 containing "Grupper"
            popular_groups_section = soup.find(
                "h3", string=lambda text: text and "Grupper" in text
            )
            if popular_groups_section:
                container = popular_groups_section.find_parent(
                    "div", class_=lambda x: x and "bg-surface-primary" in x
                )
                if container:
                    group_links = container.find_all(
                        "a", href=lambda href: href and "/grupp/" in href
                    )
                    for link in group_links:
                        name_elem = link.find("h4")
                        if name_elem:
                            name = name_elem.get_text(strip=True)
                            # Look for follower count in the same link
                            follower_text = link.get_text()
                            import re

                            follower_match = re.search(r"(\d+)", follower_text)
                            follower_count = (
                                follower_match.group(1) if follower_match else "0"
                            )
                            sidebar_data["popular_groups"].append(
                                {
                                    "name": name,
                                    "url": link.get("href", ""),
                                    "follower_count": follower_count,
                                }
                            )

            # Extract popular members - look for h3 containing "Mest följda"
            popular_members_section = soup.find(
                "h3", string=lambda text: text and "Mest följda" in text
            )
            if popular_members_section:
                container = popular_members_section.find_parent(
                    "div", class_=lambda x: x and "bg-surface-primary" in x
                )
                if container:
                    member_links = container.find_all(
                        "a", href=lambda href: href and "/medlem/" in href
                    )
                    for link in member_links:
                        name_elem = link.find("h4")
                        if name_elem:
                            name = name_elem.get_text(strip=True)
                            # Look for follower count in the same link
                            follower_text = link.get_text()
                            import re

                            follower_match = re.search(r"(\d+)", follower_text)
                            follower_count = (
                                follower_match.group(1) if follower_match else "0"
                            )
                            sidebar_data["popular_members"].append(
                                {
                                    "name": name,
                                    "url": link.get("href", ""),
                                    "follower_count": follower_count,
                                }
                            )

            return sidebar_data

        except Exception as e:
            self.logger.error(f"Error extracting sidebar data: {e}")
            return {
                "popular_posts": [],
                "popular_companies": [],
                "popular_groups": [],
                "popular_members": [],
            }

    def scrape_forum_with_sidebar(self, url: str, max_posts: int = 50) -> dict:
        """
        Scrape forum page with both posts and sidebar data.

        Args:
            url: URL of the forum page to scrape
            max_posts: Maximum number of posts to extract

        Returns:
            Dictionary containing posts and sidebar data
        """
        try:
            self.logger.info(f"Scraping forum with sidebar: {url}")

            html = self.fetch(url)
            if not html:
                self.logger.warning("Failed to fetch forum page")
                return {"posts": [], "sidebar": {}}

            # Extract posts
            posts = self.parse(html, url)
            if max_posts and len(posts) > max_posts:
                posts = posts[:max_posts]

            # Extract sidebar data
            sidebar_data = self.extract_sidebar_data(html)

            return {"posts": posts, "sidebar": sidebar_data}

        except Exception as e:
            self.logger.error(f"Error scraping forum with sidebar: {e}")
            return {"posts": [], "sidebar": {}}

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
