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
        """Fetch forum page content with redirect handling"""
        try:
            # Check robots.txt compliance
            if not check_robots_txt(url, self.user_agent):
                self.logger.warning(f"Robots.txt disallows fetching: {url}")
                return None

            # Apply polite delay
            polite_delay()

            # Fetch the page with redirect handling
            response = self.session.get(url, timeout=30, allow_redirects=True)
            response.raise_for_status()

            self.logger.info(f"Successfully fetched: {url}")
            self.logger.info(f"Final URL: {response.url}")
            self.logger.info(f"Status code: {response.status_code}")

            return response.text

        except Exception as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return None

    def parse(self, html: str) -> List[Post]:
        """Parse forum HTML and extract posts"""
        soup = BeautifulSoup(html, "html.parser")
        posts = []

        try:
            # First try to extract forum index data (thread metadata)
            posts.extend(self._extract_forum_index_data(soup))

            # Then try to extract individual post content
            posts.extend(self._extract_individual_posts(soup))

        except Exception as e:
            self.logger.error(f"Error parsing HTML: {e}")

        self.logger.info(f"Extracted {len(posts)} posts")
        return posts

    def _extract_forum_index_data(self, soup) -> List[Post]:
        """Extract thread metadata from forum index page"""
        posts = []

        try:
            # Find all thread links
            thread_links = soup.find_all("a", href=re.compile(r"/thread/\d+/view$"))

            for link in thread_links:
                try:
                    post = self._parse_thread_link(link)
                    if post:
                        posts.append(post)
                except Exception as e:
                    self.logger.warning(f"Error parsing thread link: {e}")
                    continue

            self.logger.info(f"Extracted {len(posts)} thread metadata posts")

        except Exception as e:
            self.logger.error(f"Error extracting forum index data: {e}")

        return posts

    def _parse_thread_link(self, link) -> Optional[Post]:
        """Parse a thread link to extract metadata"""
        try:
            # Get thread title
            title = link.get_text(strip=True)
            if not title:
                return None

            # Get thread URL
            href = link.get("href", "")
            if not href:
                return None

            # Extract thread ID
            thread_match = re.search(r"/thread/(\d+)/view", href)
            thread_id = thread_match.group(1) if thread_match else None

            # Find the parent row to get additional information
            parent_row = link.find_parent("tr")
            if not parent_row:
                return None

            # Extract ticker from the same row
            ticker = None
            ticker_link = parent_row.find("a", href=re.compile(r"/forum/ticker/[A-Z]+"))
            if ticker_link:
                ticker_text = ticker_link.get_text(strip=True)
                ticker_match = re.search(r"\b([A-Z]{3,5})\b", ticker_text)
                ticker = ticker_match.group(1) if ticker_match else None

            # Extract author from the same row
            author = "Unknown"
            author_link = parent_row.find("a", href=re.compile(r"/forum/user/\d+/view"))
            if author_link:
                author = author_link.get_text(strip=True)

            # Extract post count
            post_count = 0
            post_count_element = parent_row.find("span", string=re.compile(r"\d+"))
            if post_count_element:
                count_match = re.search(r"(\d+)", post_count_element.get_text())
                if count_match:
                    post_count = int(count_match.group(1))

            # Create post object
            post_url = f"https://www.finansavisen.no/forum/thread/{thread_id}/view"
            post = Post(
                forum_id=None,
                author=author,
                raw_text=title,
                clean_text=title,
                timestamp=datetime.now(),
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
            self.logger.warning(f"Error parsing thread link: {e}")
            return None

    def _extract_individual_posts(self, soup) -> List[Post]:
        """Extract individual post content from thread pages"""
        posts = []

        try:
            # Find all post containers
            post_containers = soup.find_all("div", id=re.compile(r"^post_\d+$"))
            self.logger.info(f"Found {len(post_containers)} post containers")

            for container in post_containers:
                try:
                    post = self._parse_post_container(container)
                    if post:
                        posts.append(post)
                except Exception as e:
                    self.logger.warning(f"Error parsing post container: {e}")
                    continue

            self.logger.info(f"Extracted {len(posts)} individual posts")

        except Exception as e:
            self.logger.error(f"Error extracting individual posts: {e}")

        return posts

    def _parse_post_container(self, container) -> Optional[Post]:
        """Parse a single post container to extract post information"""
        try:
            # Extract post ID
            post_id = container.get("id", "").replace("post_", "")
            if not post_id:
                return None

            # Extract author
            author_link = container.find("a", href=re.compile(r"/forum/user/\d+/view"))
            author = author_link.get_text(strip=True) if author_link else "Unknown"

            # Extract ticker
            ticker_link = container.find("a", href=re.compile(r"/forum/ticker/[A-Z]+"))
            ticker = None
            if ticker_link:
                ticker_text = ticker_link.get_text(strip=True)
                ticker_match = re.search(r"\b([A-Z]{3,5})\b", ticker_text)
                ticker = ticker_match.group(1) if ticker_match else None

            # Extract timestamp
            timestamp = None
            time_element = container.find(
                "span", string=re.compile(r"\d{2}\.\d{2}\.\d{4}")
            )
            if time_element:
                time_text = time_element.get_text(strip=True)
                # Parse Norwegian date format: "19.07.2024 kl 16:18"
                timestamp_match = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", time_text)
                if timestamp_match:
                    day, month, year = timestamp_match.groups()
                    try:
                        timestamp = datetime(int(year), int(month), int(day))
                    except ValueError:
                        timestamp = datetime.now()

            # Extract post content
            content_div = container.find("div", class_="post content text-left")
            if not content_div:
                return None

            # Get the text content, excluding any quoted content
            content_text = ""
            for element in content_div.children:
                if element.name == "blockquote":
                    # Skip quoted content
                    continue
                elif hasattr(element, "get_text"):
                    content_text += element.get_text()
                elif hasattr(element, "string") and element.string:
                    content_text += element.string

            content_text = content_text.strip()
            if not content_text or len(content_text) < 10:
                return None

            # Create post object
            post = Post(
                forum_id=None,
                author=author,
                raw_text=content_text,
                clean_text=content_text,
                timestamp=timestamp or datetime.now(),
                ticker=ticker,
                url=f"https://www.finansavisen.no/forum/post/{post_id}",
                post_id=post_id,
                metadata={
                    "source": "individual_post",
                    "content_length": len(content_text),
                    "has_ticker": ticker is not None,
                    "post_level": container.get("data-post-level", "0"),
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
