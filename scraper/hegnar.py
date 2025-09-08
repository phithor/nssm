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

    def parse(self, html: str, thread_url: str = None, thread_id: str = None) -> List[Post]:
        """Parse forum HTML and extract posts"""
        soup = BeautifulSoup(html, "html.parser")
        posts = []

        try:
            # Extract thread-level ticker information first
            thread_ticker = self._extract_thread_ticker(soup, thread_url)
            
            # First try to extract forum index data (thread metadata)
            posts.extend(self._extract_forum_index_data(soup))

            # Then try to extract individual post content with thread-level ticker
            posts.extend(self._extract_individual_posts(soup, thread_ticker, thread_url, thread_id))

        except Exception as e:
            self.logger.error(f"Error parsing HTML: {e}")

        self.logger.info(f"Extracted {len(posts)} posts")
        return posts

    def _extract_thread_ticker(self, soup, thread_url: str = None) -> str:
        """Extract ticker information from thread page"""
        try:
            # Look for ticker in thread title or breadcrumbs
            # Try multiple patterns for ticker extraction
            
            # Pattern 1: Look for ticker links in post header (individual posts)
            # Format: href="https://www.finansavisen.no/forum/ticker/AKOBO%20MINERALS"
            ticker_links = soup.find_all("a", href=re.compile(r"/forum/ticker/"))
            for link in ticker_links:
                href = link.get("href", "")
                # Extract ticker from URL - handle URL encoding
                ticker_match = re.search(r"/forum/ticker/([^/?]+)", href)
                if ticker_match:
                    ticker_raw = ticker_match.group(1)
                    # URL decode and clean up
                    import urllib.parse
                    ticker_decoded = urllib.parse.unquote(ticker_raw)
                    # Extract uppercase letters/symbols (AKOBO MINERALS -> AKOBO, BNOR -> BNOR)
                    ticker_clean = re.search(r"([A-Z]{3,5})", ticker_decoded)
                    if ticker_clean:
                        ticker = ticker_clean.group(1)
                        self.logger.debug(f"Found ticker from post header: {ticker}")
                        return ticker
            
            # Pattern 2: Look for ticker in thread title
            title_element = soup.find("h1") or soup.find("h2") or soup.find("title")
            if title_element:
                title_text = title_element.get_text(strip=True)
                # Look for ticker patterns like "AKER", "EQUI", "TEL" etc
                ticker_match = re.search(r"\b([A-Z]{3,5})\b", title_text)
                if ticker_match:
                    ticker = ticker_match.group(1)
                    # Validate it looks like a ticker (not common words)
                    if ticker not in ['THE', 'AND', 'FOR', 'ALL', 'NEW', 'OLD']:
                        self.logger.debug(f"Found thread ticker from title: {ticker}")
                        return ticker
            
            # Pattern 3: Look for ticker in URL or thread metadata
            if thread_url:
                url_ticker_match = re.search(r"/ticker/([A-Z]{3,5})", thread_url)
                if url_ticker_match:
                    ticker = url_ticker_match.group(1)
                    self.logger.debug(f"Found thread ticker from URL: {ticker}")
                    return ticker
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Error extracting thread ticker: {e}")
            return None

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

    def _extract_individual_posts(self, soup, thread_ticker=None, thread_url=None, thread_id=None) -> List[Post]:
        """Extract individual post content from thread pages"""
        posts = []

        try:
            # Find all post containers
            post_containers = soup.find_all("div", id=re.compile(r"^post_\d+$"))
            self.logger.info(f"Found {len(post_containers)} post containers")

            for container in post_containers:
                try:
                    post = self._parse_post_container(container, thread_ticker, thread_url, thread_id)
                    if post:
                        posts.append(post)
                except Exception as e:
                    self.logger.warning(f"Error parsing post container: {e}")
                    continue

            self.logger.info(f"Extracted {len(posts)} individual posts")

        except Exception as e:
            self.logger.error(f"Error extracting individual posts: {e}")

        return posts

    def _parse_post_container(self, container, thread_ticker=None, thread_url=None, thread_id=None) -> Optional[Post]:
        """Parse a single post container to extract post information"""
        try:
            # Extract post ID
            post_id = container.get("id", "").replace("post_", "")
            if not post_id:
                return None

            # Extract author
            author_link = container.find("a", href=re.compile(r"/forum/user/\d+/view"))
            author = author_link.get_text(strip=True) if author_link else "Unknown"

            # Extract ticker - use thread ticker as fallback, try post-specific ticker first
            ticker = None
            
            # First try to find ticker in this specific post (as shown in your example)
            ticker_link = container.find("a", href=re.compile(r"/forum/ticker/"))
            if ticker_link:
                href = ticker_link.get("href", "")
                ticker_match = re.search(r"/forum/ticker/([^/?]+)", href)
                if ticker_match:
                    ticker_raw = ticker_match.group(1)
                    import urllib.parse
                    ticker_decoded = urllib.parse.unquote(ticker_raw)
                    # Extract ticker symbol from decoded string
                    ticker_clean = re.search(r"([A-Z]{3,6})", ticker_decoded)
                    if ticker_clean:
                        ticker = ticker_clean.group(1)
                        self.logger.debug(f"Found post-specific ticker: {ticker}")
            
            # Use thread ticker as fallback
            if not ticker:
                ticker = thread_ticker
                if ticker:
                    self.logger.debug(f"Using thread ticker: {ticker}")

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
                thread_url=thread_url,
                post_id=post_id,
                metadata={
                    "source": "individual_post",
                    "content_length": len(content_text),
                    "has_ticker": ticker is not None,
                    "post_level": container.get("data-post-level", "0"),
                    "thread_id": thread_id,
                    "ticker_source": "post_specific" if ticker and ticker != thread_ticker else "thread_level"
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

    def scrape_forum_with_threads(self, max_pages: int = 5, max_posts_per_thread: int = 50, max_threads: int = 20, days_back: int = 30, batch_callback=None, batch_size_posts: int = 100, batch_size_threads: int = 5) -> List[Post]:
        """
        Scrape forum by getting thread lists and then scraping individual posts within threads.
        
        Args:
            max_pages: Maximum forum index pages to check for threads
            max_posts_per_thread: Maximum posts to scrape from each thread
            max_threads: Maximum number of threads to process
            days_back: Only process posts from the last N days
            batch_callback: Function to call when batch thresholds are reached (for incremental storage)
            batch_size_posts: Store posts when this many accumulate
            batch_size_threads: Store posts after processing this many threads
            
        Returns:
            List of individual posts from within threads
        """
        from datetime import datetime, timedelta
        
        all_posts = []
        thread_count = 0
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        self.logger.info(f"Starting enhanced forum scraping: {max_pages} pages, {max_threads} threads, {days_back} days back")
        
        # First, get thread IDs from forum index pages
        thread_ids = []
        for page in range(1, max_pages + 1):
            try:
                if page == 1:
                    url = f"{self.base_url}/forum/"
                else:
                    url = f"{self.base_url}/forum/?page={page}"
                
                self.logger.info(f"Getting thread IDs from forum page {page}: {url}")
                
                html = self.fetch(url)
                if html:
                    # Extract thread IDs from this page
                    page_thread_ids = self._extract_thread_ids(html)
                    thread_ids.extend(page_thread_ids)
                    self.logger.info(f"Found {len(page_thread_ids)} threads on page {page}")
                    
                    if len(page_thread_ids) == 0:
                        self.logger.info(f"No threads found on page {page}, stopping")
                        break
                else:
                    self.logger.warning(f"Failed to fetch forum page {page}")
                    break
                    
            except Exception as e:
                self.logger.error(f"Error getting thread IDs from page {page}: {e}")
                break
        
        self.logger.info(f"Found {len(thread_ids)} total threads to process")
        
        # Now scrape individual threads with batched storage
        batch_posts = []
        threads_in_current_batch = 0
        total_stored = 0
        
        for thread_id in thread_ids[:max_threads]:
            try:
                thread_count += 1
                threads_in_current_batch += 1
                self.logger.info(f"Scraping thread {thread_count}/{min(len(thread_ids), max_threads)}: {thread_id}")
                
                thread_posts = self.scrape_thread(thread_id, max_posts_per_thread)
                
                # Filter posts by date
                filtered_posts = []
                for post in thread_posts:
                    if post.timestamp and post.timestamp >= cutoff_date:
                        filtered_posts.append(post)
                
                batch_posts.extend(filtered_posts)
                all_posts.extend(filtered_posts)
                self.logger.info(f"Added {len(filtered_posts)} posts from thread {thread_id} (filtered from {len(thread_posts)} total)")
                
                # Check if we should trigger batch storage
                should_store_batch = (
                    batch_callback and 
                    (len(batch_posts) >= batch_size_posts or 
                     threads_in_current_batch >= batch_size_threads)
                )
                
                if should_store_batch:
                    self.logger.info(f"Triggering batch storage: {len(batch_posts)} posts from {threads_in_current_batch} threads")
                    stored_count = batch_callback(batch_posts)
                    total_stored += stored_count
                    self.logger.info(f"Batch stored {stored_count} posts (total stored: {total_stored})")
                    
                    # Reset batch
                    batch_posts = []
                    threads_in_current_batch = 0
                
            except Exception as e:
                self.logger.error(f"Error scraping thread {thread_id}: {e}")
                continue
        
        # Store any remaining posts in final batch
        if batch_callback and batch_posts:
            self.logger.info(f"Storing final batch: {len(batch_posts)} posts from {threads_in_current_batch} threads")
            stored_count = batch_callback(batch_posts)
            total_stored += stored_count
            self.logger.info(f"Final batch stored {stored_count} posts (total stored: {total_stored})")
        
        self.logger.info(f"Enhanced scraping complete: {len(all_posts)} posts from {thread_count} threads")
        return all_posts
    
    def _extract_thread_ids(self, html: str) -> List[str]:
        """Extract thread IDs from forum index page HTML"""
        from bs4 import BeautifulSoup
        import re
        
        thread_ids = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Find all thread links
            thread_links = soup.find_all("a", href=re.compile(r"/forum/thread/(\d+)"))
            
            for link in thread_links:
                href = link.get("href", "")
                thread_match = re.search(r"/forum/thread/(\d+)", href)
                if thread_match:
                    thread_id = thread_match.group(1)
                    if thread_id not in thread_ids:  # Avoid duplicates
                        thread_ids.append(thread_id)
        
        except Exception as e:
            self.logger.error(f"Error extracting thread IDs: {e}")
        
        return thread_ids

    def scrape_thread(self, thread_id: str, max_posts: int = 50) -> List[Post]:
        """Scrape a specific thread for posts"""
        try:
            url = f"{self.base_url}/forum/thread/{thread_id}/view"
            self.logger.info(f"Scraping thread {thread_id}: {url}")

            html = self.fetch(url)
            if html:
                posts = self.parse(html, thread_url=url, thread_id=thread_id)
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
