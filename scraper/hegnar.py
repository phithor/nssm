"""
Hegnar/Finansavisen Forum Scraper

This scraper extracts posts from the Finansavisen forum (formerly Hegnar).
The forum uses a traditional HTML table structure with specific CSS classes.
"""

import logging
import re
from datetime import datetime
from typing import List, Optional

from bs4 import BeautifulSoup

from db.models import Post

from .base import Scraper
from .utils import check_robots_txt, polite_delay


class HegnarScraper(Scraper):
    """Scraper for Finansavisen forum (formerly Hegnar)"""

    def __init__(self):
        super().__init__("https://www.finansavisen.no")
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def fetch(self, url: str, **kwargs) -> Optional[str]:
        """Fetch forum page content"""
        try:
            # Check robots.txt compliance
            if not check_robots_txt(url, self.user_agent):
                self.logger.warning(f"Robots.txt disallows fetching: {url}")
                return None

            # Apply polite delay
            polite_delay()

            # Fetch the page
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            self.logger.info(f"Successfully fetched: {url}")
            return response.text

        except Exception as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return None

    def parse(self, html: str) -> List[Post]:
        """Parse forum HTML and extract posts"""
        soup = BeautifulSoup(html, "html.parser")
        posts = []

        try:
            # Find all thread rows in the forum index
            thread_rows = soup.find_all("tr", class_=re.compile(r"thread.*list-row"))

            for row in thread_rows:
                try:
                    post = self._parse_thread_row(row)
                    if post:
                        posts.append(post)
                except Exception as e:
                    self.logger.warning(f"Error parsing thread row: {e}")
                    continue

            # Also look for individual posts in thread pages
            post_containers = soup.find_all("div", id=re.compile(r"post_\d+"))

            for container in post_containers:
                try:
                    post = self._parse_post_container(container)
                    if post:
                        posts.append(post)
                except Exception as e:
                    self.logger.warning(f"Error parsing post container: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error parsing HTML: {e}")

        self.logger.info(f"Extracted {len(posts)} posts")
        return posts

    def _parse_thread_row(self, row) -> Optional[Post]:
        """Parse a thread row from the forum index"""
        try:
            # Extract thread ID
            thread_id = row.get("data-thread")
            if not thread_id:
                return None

            # Extract ticker from thread-ticker column
            ticker_cell = row.find("td", class_="thread-ticker")
            ticker = None
            if ticker_cell:
                ticker_text = ticker_cell.get_text(strip=True)
                # Extract ticker using regex (common patterns like 3-4 letter codes)
                ticker_match = re.search(r"\b[A-Z]{2,5}\b", ticker_text)
                if ticker_match:
                    ticker = ticker_match.group()

            # Extract thread title
            title_link = row.find("a", class_="thread")
            title = title_link.get_text(strip=True) if title_link else "No title"

            # Extract author
            author_cell = row.find("td", class_="thread-nick")
            author = None
            if author_cell:
                author_link = author_cell.find("a")
                author = (
                    author_link.get_text(strip=True) if author_link else "Anonymous"
                )

            # Extract post count
            post_count_link = row.find("a", href=re.compile(r"/view/\d+"))
            post_count = 0
            if post_count_link:
                count_text = post_count_link.get_text(strip=True)
                count_match = re.search(r"\[(\d+)\]", count_text)
                if count_match:
                    post_count = int(count_match.group(1))

            # Create post object
            post_url = f"https://www.finansavisen.no/forum/thread/{thread_id}/view"
            post = Post(
                forum_id=None,  # Will be set by persistence layer
                author=author or "Anonymous",
                raw_text=title,
                clean_text=title,  # For now, same as raw_text
                timestamp=datetime.now(),  # Forum index doesn't show post timestamps
                ticker=ticker,
                url=post_url,
                post_id=f"thread_{thread_id}",
                metadata={
                    "thread_id": thread_id,
                    "post_count": post_count,
                    "source": "forum_index",
                },
            )

            return post

        except Exception as e:
            self.logger.warning(f"Error parsing thread row: {e}")
            return None

    def _parse_post_container(self, container) -> Optional[Post]:
        """Parse an individual post container"""
        try:
            # Extract post ID
            post_id = container.get("id", "").replace("post_", "")
            if not post_id:
                return None

            # Extract author
            author_link = container.find("a", href=re.compile(r"/user/\d+/view"))
            author = None
            if author_link:
                author = author_link.get_text(strip=True)

            # Extract timestamp
            timestamp = None
            timestamp_span = container.find(
                "span", string=re.compile(r"\d{2}\.\d{2}\.\d{4}")
            )
            if timestamp_span:
                timestamp_text = timestamp_span.get_text(strip=True)
                try:
                    # Parse Norwegian timestamp format: "13.08.2025 kl 10:42"
                    timestamp = datetime.strptime(timestamp_text, "%d.%m.%Y kl %H:%M")
                except ValueError:
                    self.logger.warning(f"Could not parse timestamp: {timestamp_text}")

            # Extract content
            content_div = container.find("div", class_="post content")
            content = None
            if content_div:
                content = content_div.get_text(strip=True)

            # Extract ticker from content using regex
            ticker = None
            if content:
                # Look for common ticker patterns in Norwegian text
                ticker_match = re.search(r"\b[A-Z]{2,5}\b", content)
                if ticker_match:
                    ticker = ticker_match.group()

            # Create post object
            post = Post(
                forum_id=None,  # Will be set by persistence layer
                author=author or "Anonymous",
                raw_text=content or "No content",
                clean_text=content or "No content",  # For now, same as raw_text
                timestamp=timestamp or datetime.now(),
                ticker=ticker,
                url=f"https://www.finansavisen.no/forum/post/{post_id}",
                post_id=post_id,
                metadata={
                    "source": "individual_post",
                    "container_id": container.get("id"),
                },
            )

            return post

        except Exception as e:
            self.logger.warning(f"Error parsing post container: {e}")
            return None

    def scrape_forum_index(self, max_pages: int = 5) -> List[Post]:
        """Scrape the main forum index page"""
        posts = []

        for page in range(1, max_pages + 1):
            try:
                if page == 1:
                    url = f"{self.base_url}/forum/"
                else:
                    url = f"{self.base_url}/forum/?page={page}"

                self.logger.info(f"Scraping forum index page {page}: {url}")

                html = self.fetch(url)
                if html:
                    page_posts = self.parse(html)
                    posts.extend(page_posts)

                    if len(page_posts) == 0:
                        self.logger.info(
                            f"No more posts found on page {page}, stopping"
                        )
                        break
                else:
                    self.logger.warning(f"Failed to fetch page {page}")
                    break

            except Exception as e:
                self.logger.error(f"Error scraping page {page}: {e}")
                break

        return posts

    def scrape_thread(self, thread_id: str, max_posts: int = 50) -> List[Post]:
        """Scrape a specific thread for posts"""
        try:
            url = f"{self.base_url}/forum/thread/{thread_id}/view"
            self.logger.info(f"Scraping thread {thread_id}: {url}")

            html = self.fetch(url)
            if html:
                posts = self.parse(html)
                # Limit posts if needed
                if max_posts and len(posts) > max_posts:
                    posts = posts[:max_posts]
                return posts
            else:
                self.logger.warning(f"Failed to fetch thread {thread_id}")
                return []

        except Exception as e:
            self.logger.error(f"Error scraping thread {thread_id}: {e}")
            return []
