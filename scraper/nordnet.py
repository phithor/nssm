"""
Nordnet Shareville Forum Scraper

Scrapes posts from Nordnet Shareville (https://www.nordnet.no/shareville)
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


class NordnetScraper(Scraper):
    """
    Scraper for Nordnet Shareville with Selenium fallback.

    Scrapes posts from https://www.nordnet.no/shareville with automatic detection
    and appropriate selectors for the platform.
    """

    def __init__(self, use_selenium_fallback: bool = True):
        """
        Initialize scraper with configuration.

        Args:
            use_selenium_fallback: Whether to use Selenium as fallback
        """
        super().__init__(
            base_url="https://www.nordnet.no",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.use_selenium_fallback = use_selenium_fallback

        # Ticker regex pattern for Norwegian stocks
        self.ticker_pattern = re.compile(r"\b[A-Z]{2,6}\b")

        # Nordnet Shareville selectors based on actual HTML structure
        self.selectors = {
            "post_container": "li.ListItem__StyledListItem-sc-pn91gs-0",
            "author_container": (
                "div.Flexbox__StyledFlexbox-sc-1ob4g1e-0.hqaqcx > "
                "a.Link__StyledLink-sc-apj04t-0"
            ),
            "author_name": (
                "div.Flexbox__StyledFlexbox-sc-1ob4g1e-0.haAnAc > "
                "span > a.Link__StyledLink-sc-apj04t-0"
            ),
            "ticker": "a[data-testid='ticker'], .ticker, .stock-symbol",
            "title": "h3, h4, .post-title",
            "content": (
                "div.Content-styled__MarkContentFlexbox-sc-d426b66b-3 > "
                "div.CssGrid__StyledDiv-sc-bu5cxy-0"
            ),
            "timestamp": (
                "div.Flexbox__StyledFlexbox-sc-1ob4g1e-0.hllVYC > "
                "span.Typography__Span-sc-10mju41-0"
            ),
            "pagination": ".pagination, .pages, .page-nav",
            "shareville_section": "div[data-testid='shareville-section'], .shareville, ul",
            "likes": (
                "button.NormalizedButton__Button-sc-ey7f5x-0."
                "Button__StyledButton-sc-rtfjm6-0.glaBYD"
            ),
            "likes_count": "span.lmVbIM, .likes-count",
            "nested_posts": (
                "li.ListItem__StyledListItem-sc-pn91gs-0 "
                "li.ListItem__StyledListItem-sc-pn91gs-0"
            ),
        }

        # Initialize Selenium wrapper if fallback is enabled
        self.selenium_wrapper = None
        if self.use_selenium_fallback:
            self.selenium_wrapper = SeleniumWrapper(headless=True)

        # Known ticker URL mappings
        self.ticker_urls = {
            "ENSU": "https://www.nordnet.no/aksjer/kurser/ensurge-micropower-ensu-xosl",
            "NOVO": "https://www.nordnet.no/aksjer/kurser/novo-nordisk-b-novo-b-xcse",
            # Add more mappings as discovered
        }

    def fetch(self, url: str, **kwargs) -> Optional[str]:
        """
        Fetch content from Nordnet Shareville pages with automatic fallback.

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
            headers.update(self.session.headers)

            # Add Nordnet-specific headers
            headers.update(
                {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "nb-NO,nb;q=0.9,en;q=0.8",
                    "Referer": "https://www.nordnet.no/",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "same-origin",
                }
            )

            response = self.session.get(url, headers=headers, timeout=30, **kwargs)
            response.raise_for_status()

            # Add polite delay between requests
            polite_delay()

            return response.text

        except requests.RequestException as e:
            self.logger.error(f"Request failed for {url}: {e}")
            return None

    def _fetch_with_selenium(self, url: str) -> Optional[str]:
        """Fetch content using Selenium when JavaScript rendering is needed."""
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
        Check if the HTML content requires JavaScript rendering.

        Args:
            html: HTML content to check

        Returns:
            True if JavaScript fallback is needed
        """
        # Check for common indicators of JavaScript-rendered content
        indicators = [
            "Loading...",
            "Please wait",
            "JavaScript is required",
            "noscript",
            "react-root",
            "vue-app",
            "angular-app",
        ]

        soup = BeautifulSoup(html, "html.parser")

        # Check if Shareville content is present
        shareville_content = soup.find("div", {"data-testid": "shareville-section"})
        if not shareville_content:
            return True

        # Check for loading indicators
        for indicator in indicators:
            if indicator.lower() in html.lower():
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
        soup = BeautifulSoup(html, "html.parser")

        # Look for Shareville section - try multiple approaches
        shareville_section = soup.find("div", {"data-testid": "shareville-section"})
        if not shareville_section:
            # Try alternative selectors
            shareville_section = soup.find("div", class_="shareville")

        if not shareville_section:
            # Look for the main content area with posts
            shareville_section = soup.find("ul") or soup.find(
                "div", class_="Card__StyledCard-sc-1e5czjc-0"
            )

        if not shareville_section:
            self.logger.warning("Could not find Shareville section in HTML")
            return posts

        # Find all post containers - use the actual HTML structure
        post_containers = shareville_section.find_all(
            "li", class_="ListItem__StyledListItem-sc-pn91gs-0"
        )

        if not post_containers:
            # Fallback to any li elements that might contain posts
            post_containers = shareville_section.find_all("li")

        if not post_containers:
            # Try alternative selectors
            post_containers = shareville_section.find_all(
                "article"
            ) or shareville_section.find_all("div", class_="post-card")

        self.logger.info(f"Found {len(post_containers)} post containers")

        for container in post_containers:
            try:
                post = self._parse_post_container(container)
                if post:
                    posts.append(post)
            except Exception as e:
                self.logger.warning(f"Error parsing post container: {e}")
                continue

        return posts

    def _parse_post_container(self, container) -> Optional[Post]:
        """
        Parse a single post container into a Post object.

        Args:
            container: BeautifulSoup element containing post data

        Returns:
            Post object or None if parsing failed
        """
        try:
            # Extract author - use the actual HTML structure
            author_elem = container.select_one(
                "div.Flexbox__StyledFlexbox-sc-1ob4g1e-0.haAnAc > span > a.Link__StyledLink-sc-apj04t-0"
            )
            if not author_elem:
                author_elem = container.find("a", class_="Link__StyledLink-sc-apj04t-0")
            if not author_elem:
                author_elem = container.find("a", {"data-testid": "author-name"})
            if not author_elem:
                author_elem = container.find(
                    "span", class_="author-name"
                ) or container.find("div", class_="username")

            author = author_elem.get_text(strip=True) if author_elem else "Unknown"

            # Extract ticker - look for ticker in the content or URL
            ticker = None
            ticker_elem = container.find("a", {"data-testid": "ticker"})
            if not ticker_elem:
                ticker_elem = container.find("span", class_="ticker") or container.find(
                    "div", class_="stock-symbol"
                )

            if ticker_elem:
                ticker_text = ticker_elem.get_text(strip=True)
                # Extract ticker using regex
                match = self.ticker_pattern.search(ticker_text)
                if match:
                    ticker = match.group()

            # If no ticker found in dedicated element, try to extract from content
            if not ticker:
                # Look for ticker in the content text
                content_text = container.get_text()
                match = self.ticker_pattern.search(content_text)
                if match:
                    ticker = match.group()

            # Extract title - might not be present in comments
            title_elem = (
                container.find("h3")
                or container.find("h4")
                or container.find("div", class_="post-title")
            )
            title = title_elem.get_text(strip=True) if title_elem else ""

            # Extract content - use the actual HTML structure
            content_elem = container.select_one(
                "div.Content-styled__MarkContentFlexbox-sc-d426b66b-3 > div.CssGrid__StyledDiv-sc-bu5cxy-0"
            )
            if not content_elem:
                content_elem = container.find(
                    "span", class_="ContentMessage-styled__ShortenedText-sc-5bd6ed6d-1"
                )
            if not content_elem:
                content_elem = (
                    container.find("div", class_="post-body")
                    or container.find("div", class_="post-content")
                    or container.find("div", class_="content")
                )

            content = content_elem.get_text(strip=True) if content_elem else ""

            # Combine title and content
            raw_text = f"{title}\n\n{content}".strip()

            # Extract timestamp - use the actual HTML structure
            timestamp_elem = container.select_one(
                "div.Flexbox__StyledFlexbox-sc-1ob4g1e-0.hllVYC > span.Typography__Span-sc-10mju41-0"
            )
            if not timestamp_elem:
                timestamp_elem = container.find("span", class_="gAAhrK")
            if not timestamp_elem:
                timestamp_elem = container.find(
                    "span", class_="Typography__Span-sc-10mju41-0"
                )
            if not timestamp_elem:
                timestamp_elem = container.find("span", {"data-testid": "timestamp"})
            if not timestamp_elem:
                timestamp_elem = container.find(
                    "span", class_="timestamp"
                ) or container.find("span", class_="date")

            timestamp = datetime.now()  # Default to now
            if timestamp_elem:
                timestamp_text = timestamp_elem.get_text(strip=True)
                timestamp = self._parse_timestamp(timestamp_text)

            # Extract post URL
            post_url = None
            link_elem = container.find("a", href=True)
            if link_elem:
                post_url = self.get_full_url(link_elem["href"])

            # Extract likes count if available
            likes_count = None
            like_button = container.select_one(
                "button.NormalizedButton__Button-sc-ey7f5x-0.Button__StyledButton-sc-rtfjm6-0.glaBYD"
            )
            if not like_button:
                like_button = container.find("button", attrs={"aria-label": "Lik"})
            if like_button:
                likes_span = like_button.find("span", class_="lmVbIM")
                if likes_span:
                    likes_count = likes_span.get_text(strip=True)

            # Generate unique post ID
            post_id = f"nordnet_{hash(f'{author}_{timestamp}_{title}')}"

            # Create Post object
            post = Post(
                forum_id=0,  # Will be set by persistence layer
                post_id=post_id,
                ticker=ticker,
                timestamp=timestamp,
                author=author,
                raw_text=raw_text,
                clean_text=raw_text,  # Will be cleaned by NLP pipeline
                url=post_url,
                scraper_metadata={
                    "source": "nordnet_shareville",
                    "parsed_at": datetime.now().isoformat(),
                    "title": title,
                    "likes_count": likes_count,
                },
            )

            return post

        except Exception as e:
            self.logger.warning(f"Error parsing post container: {e}")
            return None

    def _parse_timestamp(self, timestamp_text: str) -> datetime:
        """
        Parse timestamp text into datetime object.

        Args:
            timestamp_text: Timestamp text from the page

        Returns:
            Parsed datetime object
        """
        try:
            # Handle Norwegian date formats
            # Examples: "for 1 døgn siden", "2 timer siden", "15. aug.", "2024-08-15"

            if "døgn" in timestamp_text or "dager" in timestamp_text:
                # Relative time like "for 1 døgn siden"
                return datetime.now()

            if "timer" in timestamp_text or "minutter" in timestamp_text:
                # Relative time like "2 timer siden"
                return datetime.now()

            # Try to parse absolute dates
            # Norwegian month abbreviations
            month_map = {
                "jan": 1,
                "feb": 2,
                "mar": 3,
                "apr": 4,
                "mai": 5,
                "jun": 6,
                "jul": 7,
                "aug": 8,
                "sep": 9,
                "okt": 10,
                "nov": 11,
                "des": 12,
            }

            # Try format like "15. aug."
            for month_name, month_num in month_map.items():
                if month_name in timestamp_text.lower():
                    # Extract day and year
                    parts = timestamp_text.split(".")
                    if len(parts) >= 2:
                        day = int(parts[0])
                        year = datetime.now().year  # Assume current year
                        return datetime(year, month_num, day)

            # Try ISO format
            if "-" in timestamp_text:
                return datetime.fromisoformat(timestamp_text.replace("Z", "+00:00"))

            # Default to now if parsing fails
            return datetime.now()

        except Exception as e:
            self.logger.warning(f"Error parsing timestamp '{timestamp_text}': {e}")
            return datetime.now()

    def scrape_ticker_posts(self, ticker: str, max_pages: int = 5) -> List[Post]:
        """
        Scrape posts for a specific ticker.

        Args:
            ticker: Stock ticker to search for
            max_pages: Maximum number of pages to scrape

        Returns:
            List of Post objects
        """
        posts = []

        # Try to construct the correct URL for the ticker
        # The URL format is: https://www.nordnet.no/aksjer/kurser/{company-name}-{ticker}-{exchange}
        # We need to handle different exchanges and company name variations

        # Common Norwegian exchanges and their suffixes
        exchanges = {
            "OSL": "xosl",  # Oslo Børs
            "CSE": "xcse",  # Copenhagen Stock Exchange
            "STO": "xsto",  # Stockholm Stock Exchange
            "HEL": "xhel",  # Helsinki Stock Exchange
        }

        # Try different URL patterns for the ticker
        url_patterns = []

        # Pattern 1: Check if we have a known URL mapping
        if ticker.upper() in self.ticker_urls:
            url_patterns.append(self.ticker_urls[ticker.upper()])

        # Pattern 2: Direct ticker with common exchanges
        for exchange_suffix in exchanges.values():
            url_patterns.append(
                f"https://www.nordnet.no/aksjer/kurser/{ticker.lower()}-{exchange_suffix}"
            )

        # Pattern 3: Try with just the ticker (fallback)
        url_patterns.append(f"https://www.nordnet.no/aksjer/kurser/{ticker.lower()}")

        # Try each URL pattern until one works
        working_url = None
        for url_pattern in url_patterns:
            try:
                test_html = self.fetch(url_pattern)
                if test_html and "Shareville" in test_html:
                    working_url = url_pattern
                    self.logger.info(f"Found working URL for {ticker}: {working_url}")
                    break
            except Exception as e:
                self.logger.debug(f"URL pattern {url_pattern} failed for {ticker}: {e}")
                continue

        if not working_url:
            self.logger.warning(f"Could not find working URL for ticker {ticker}")
            return posts

        # Now scrape using the working URL
        for page in range(1, max_pages + 1):
            try:
                url = f"{working_url}?page={page}" if page > 1 else working_url
                self.logger.info(f"Scraping page {page} for ticker {ticker}: {url}")

                html = self.fetch(url)
                if not html:
                    self.logger.warning(f"Failed to fetch page {page} for {ticker}")
                    break

                page_posts = self.parse(html)
                posts.extend(page_posts)

                self.logger.info(f"Found {len(page_posts)} posts on page {page}")

                # Stop if no posts found (likely reached end)
                if not page_posts:
                    break

            except Exception as e:
                self.logger.error(f"Error scraping page {page} for {ticker}: {e}")
                break

        return posts

    def scrape_all_posts(self, max_pages: int = 5) -> List[Post]:
        """
        Scrape posts from Nordnet Shareville for all stocks.

        Args:
            max_pages: Maximum number of pages to scrape

        Returns:
            List of Post objects
        """
        posts = []

        # Try different main forum URLs
        # Based on the user's information, the main forum URL is: https://www.nordnet.no/aksjeforum
        forum_urls = [
            "https://www.nordnet.no/aksjeforum",  # Main forum URL
            "https://www.nordnet.no/shareville",  # Alternative URL
        ]

        working_url = None
        for forum_url in forum_urls:
            try:
                test_html = self.fetch(forum_url)
                if test_html and (
                    "Shareville" in test_html or "aksjeforum" in test_html
                ):
                    working_url = forum_url
                    self.logger.info(f"Found working forum URL: {working_url}")
                    break
            except Exception as e:
                self.logger.debug(f"Forum URL {forum_url} failed: {e}")
                continue

        if not working_url:
            self.logger.warning("Could not find working forum URL")
            return posts

        # Now scrape using the working URL
        for page in range(1, max_pages + 1):
            try:
                url = f"{working_url}?page={page}" if page > 1 else working_url
                self.logger.info(f"Scraping page {page} for all stocks: {url}")

                html = self.fetch(url)
                if not html:
                    self.logger.warning(f"Failed to fetch page {page}")
                    break

                page_posts = self.parse(html)
                posts.extend(page_posts)

                self.logger.info(f"Found {len(page_posts)} posts on page {page}")

                # Stop if no posts found (likely reached end)
                if not page_posts:
                    break

            except Exception as e:
                self.logger.error(f"Error scraping page {page}: {e}")
                break

        return posts

    def close(self):
        """Close the scraper and clean up resources."""
        if self.selenium_wrapper:
            self.selenium_wrapper.close()
        super().close()
