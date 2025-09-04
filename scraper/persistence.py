"""
Database persistence layer for forum scrapers

Handles database operations for storing scraped forum posts
and managing forum metadata.
"""

import logging
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from db import SessionLocal
from db.models import Forum, Post

from .avanza import PlaceraScraper
from .hegnar import HegnarScraper
from .nordnet import NordnetScraper


class ScraperPersistence:
    """Handles database persistence for scraped forum data"""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.hegnar_scraper = HegnarScraper()
        self.avanza_scraper = PlaceraScraper()
        self.nordnet_scraper = NordnetScraper()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        # Clean up if needed
        pass

    def get_post_count_by_forum(self) -> Dict[str, int]:
        """Get post count by forum name"""
        try:
            with SessionLocal() as session:
                forum_counts = (
                    session.query(Forum.name, Forum.id, Post.id)
                    .join(Post, Forum.id == Post.forum_id)
                    .group_by(Forum.name, Forum.id)
                    .all()
                )

                return {name: count for name, forum_id, count in forum_counts}
        except Exception as e:
            self.logger.error(f"Error getting post count by forum: {e}")
            return {}

    def get_forum_id(self, forum_name: str) -> Optional[int]:
        """Get forum ID by name"""
        try:
            with SessionLocal() as session:
                forum = session.query(Forum).filter(Forum.name == forum_name).first()
                return forum.id if forum else None
        except Exception as e:
            self.logger.error(f"Error getting forum ID for {forum_name}: {e}")
            return None

    def upsert_posts(self, posts: List[Post], session: Optional[Session] = None) -> int:
        """Insert or update posts, handling duplicates"""
        if not posts:
            return 0

        use_session = session or SessionLocal()
        inserted_count = 0

        try:
            for post in posts:
                try:
                    # Check if post already exists
                    existing_post = (
                        use_session.query(Post)
                        .filter(
                            Post.post_id == post.post_id, Post.forum_id == post.forum_id
                        )
                        .first()
                    )

                    if existing_post:
                        # Update existing post
                        existing_post.content = post.content
                        existing_post.timestamp = post.timestamp
                        existing_post.ticker = post.ticker
                        existing_post.metadata = post.metadata
                        self.logger.debug(f"Updated existing post: {post.post_id}")
                    else:
                        # Insert new post
                        use_session.add(post)
                        inserted_count += 1
                        self.logger.debug(f"Inserted new post: {post.post_id}")

                except Exception as e:
                    self.logger.warning(f"Error processing post {post.post_id}: {e}")
                    continue

            if not session:  # Only commit if we created the session
                use_session.commit()
                self.logger.info(
                    f"Successfully processed {len(posts)} posts, {inserted_count} new"
                )

            return inserted_count

        except Exception as e:
            if not session:
                use_session.rollback()
            self.logger.error(f"Error upserting posts: {e}")
            raise
        finally:
            if not session:
                use_session.close()

    def bulk_insert_posts(
        self, posts: List[Post], session: Optional[Session] = None
    ) -> int:
        """Bulk insert posts without duplicate checking"""
        if not posts:
            return 0

        use_session = session or SessionLocal()

        try:
            use_session.bulk_save_objects(posts)

            if not session:
                use_session.commit()
                self.logger.info(f"Bulk inserted {len(posts)} posts")

            return len(posts)

        except Exception as e:
            if not session:
                use_session.rollback()
            self.logger.error(f"Error bulk inserting posts: {e}")
            raise
        finally:
            if not session:
                use_session.close()

    def scrape_and_store_hegnar(self, max_pages: int = 5) -> Dict[str, any]:
        """Scrape Hegnar/Finansavisen forum and store posts"""
        try:
            self.logger.info("Starting Hegnar/Finansavisen forum scraping")

            # Get forum ID
            forum_id = self.get_forum_id("Hegnar Online")
            if not forum_id:
                self.logger.error("Hegnar Online forum not found in database")
                return {"success": False, "error": "Forum not found"}

            # Scrape forum index
            posts = self.hegnar_scraper.scrape_forum_index(max_pages)

            if not posts:
                self.logger.warning("No posts found from Hegnar forum")
                return {"success": True, "posts_found": 0, "posts_stored": 0}

            # Set forum ID for all posts
            for post in posts:
                post.forum_id = forum_id

            # Store posts
            stored_count = self.upsert_posts(posts)

            return {
                "success": True,
                "posts_found": len(posts),
                "posts_stored": stored_count,
                "forum": "Hegnar Online",
            }

        except Exception as e:
            self.logger.error(f"Error scraping Hegnar forum: {e}")
            return {"success": False, "error": str(e)}

    def scrape_and_store_placera(self, max_posts: int = 50) -> Dict[str, any]:
        """Scrape Placera forum and store posts"""
        try:
            self.logger.info("Starting Placera forum scraping")

            # Get forum ID
            forum_id = self.get_forum_id("Placera Forum")
            if not forum_id:
                self.logger.error("Placera Forum not found in database")
                return {"success": False, "error": "Forum not found"}

            # Scrape forum feed
            posts = self.avanza_scraper.scrape_forum_feed(max_posts)

            if not posts:
                self.logger.warning("No posts found from Placera forum")
                return {"success": True, "posts_found": 0, "posts_stored": 0}

            # Set forum ID for all posts
            for post in posts:
                post.forum_id = forum_id

            # Store posts
            stored_count = self.upsert_posts(posts)

            return {
                "success": True,
                "posts_found": len(posts),
                "posts_stored": stored_count,
                "forum": "Placera Forum",
            }

        except Exception as e:
            self.logger.error(f"Error scraping Placera forum: {e}")
            return {"success": False, "error": str(e)}

    def scrape_and_store_nordnet(
        self, ticker: str = None, max_pages: int = 5
    ) -> Dict[str, any]:
        """Scrape Nordnet Shareville forum and store posts for a specific ticker or all stocks"""
        try:
            if ticker:
                self.logger.info(
                    f"Starting Nordnet Shareville scraping for ticker {ticker}"
                )
            else:
                self.logger.info("Starting Nordnet Shareville scraping for all stocks")

            # Get forum ID
            forum_id = self.get_forum_id("Nordnet Shareville")
            if not forum_id:
                self.logger.error("Nordnet Shareville forum not found in database")
                return {"success": False, "error": "Forum not found"}

            # Scrape posts
            if ticker:
                posts = self.nordnet_scraper.scrape_ticker_posts(ticker, max_pages)
            else:
                posts = self.nordnet_scraper.scrape_all_posts(max_pages)

            if not posts:
                ticker_msg = f" for {ticker}" if ticker else ""
                self.logger.warning(
                    f"No posts found from Nordnet Shareville{ticker_msg}"
                )
                return {"success": True, "posts_found": 0, "posts_stored": 0}

            # Set forum ID for all posts
            for post in posts:
                post.forum_id = forum_id

            # Store posts
            stored_count = self.upsert_posts(posts)

            return {
                "success": True,
                "posts_found": len(posts),
                "posts_stored": stored_count,
                "forum": "Nordnet Shareville",
                "ticker": ticker or "all",
            }

        except Exception as e:
            self.logger.error(f"Error scraping Nordnet Shareville forum: {e}")
            return {"success": False, "error": str(e)}

    def scrape_all_forums(
        self, max_pages: int = 5, max_posts: int = 50
    ) -> Dict[str, any]:
        """Scrape all configured forums and store posts"""
        results = {}

        try:
            self.logger.info("Starting scraping for all forums")

            # Scrape Hegnar/Finansavisen
            hegnar_result = self.scrape_and_store_hegnar(max_pages)
            results["hegnar"] = hegnar_result

            # Scrape Placera
            placera_result = self.scrape_and_store_placera(max_posts)
            results["placera"] = placera_result

            # Scrape Nordnet Shareville for all stocks
            nordnet_result = self.scrape_and_store_nordnet(max_pages=max_pages)
            results["nordnet"] = nordnet_result

            # Summary
            total_posts = sum(
                r.get("posts_found", 0) for r in results.values() if r.get("success")
            )
            total_stored = sum(
                r.get("posts_stored", 0) for r in results.values() if r.get("success")
            )

            results["summary"] = {
                "total_posts_found": total_posts,
                "total_posts_stored": total_stored,
                "all_successful": all(
                    r.get("success", False) for r in results.values()
                ),
            }

            self.logger.info(
                f"Completed scraping all forums. "
                f"Total: {total_posts} found, {total_stored} stored"
            )

        except Exception as e:
            self.logger.error(f"Error in scrape_all_forums: {e}")
            results["error"] = str(e)

        return results

    def get_forum_stats(self) -> Dict[str, any]:
        """Get statistics about stored forum data"""
        try:
            with SessionLocal() as session:
                # Count posts by forum
                forum_counts = (
                    session.query(Forum.name, Forum.id, Post.id)
                    .join(Post, Forum.id == Post.forum_id)
                    .group_by(Forum.name, Forum.id)
                    .all()
                )

                # Total post count
                total_posts = session.query(Post).count()

                # Recent posts (last 24 hours)
                from datetime import datetime, timedelta

                yesterday = datetime.now() - timedelta(days=1)
                recent_posts = (
                    session.query(Post).filter(Post.timestamp >= yesterday).count()
                )

                return {
                    "total_posts": total_posts,
                    "recent_posts_24h": recent_posts,
                    "forums": [
                        {"name": name, "id": forum_id, "post_count": post_count}
                        for name, forum_id, post_count in forum_counts
                    ],
                }

        except Exception as e:
            self.logger.error(f"Error getting forum stats: {e}")
            return {"error": str(e)}

    def cleanup_old_posts(self, days_old: int = 30) -> int:
        """Remove posts older than specified days"""
        try:
            from datetime import datetime, timedelta

            cutoff_date = datetime.now() - timedelta(days=days_old)

            with SessionLocal() as session:
                deleted_count = (
                    session.query(Post).filter(Post.timestamp < cutoff_date).delete()
                )
                session.commit()

                self.logger.info(
                    f"Cleaned up {deleted_count} posts older than {days_old} days"
                )
                return deleted_count

        except Exception as e:
            self.logger.error(f"Error cleaning up old posts: {e}")
            return 0
