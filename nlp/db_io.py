"""
Database I/O Layer for NLP Sentiment Analysis

Handles database operations for fetching unscored posts and storing sentiment results,
with proper error handling, transactions, and performance optimizations.
"""

import time
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select, text, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db.models import Post

from .infer import BatchInferenceResult, SentimentResult


class SentimentDBHandler:
    """Handles database operations for sentiment analysis workflow."""

    def __init__(self, session_factory: callable):
        """
        Initialize the database handler.

        Args:
            session_factory: Function that returns a SQLAlchemy session
        """
        self.session_factory = session_factory

    def fetch_unscored_posts(
        self,
        limit: int = 100,
        language_hint: Optional[str] = None,
        forum_ids: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch posts that haven't been analyzed for sentiment yet.

        Args:
            limit: Maximum number of posts to fetch
            language_hint: Optional language filter ('no' or 'sv')
            forum_ids: Optional list of forum IDs to filter by

        Returns:
            List of post dictionaries with id, text, forum_id, etc.
        """
        try:
            with self.session_factory() as session:
                # Build query for posts without sentiment scores
                query = (
                    select(
                        Post.id,
                        Post.raw_text.label("text"),
                        Post.forum_id,
                        Post.ticker,
                        Post.timestamp,
                        Post.author,
                    )
                    .where(
                        and_(
                            Post.sentiment_score.is_(None),  # No sentiment score yet
                            Post.raw_text.is_not(None),  # Has text content
                            Post.raw_text != "",  # Text is not empty
                        )
                    )
                    .order_by(Post.timestamp.desc())  # Process newest posts first
                    .limit(limit)
                )

                # Add forum filter if specified
                if forum_ids:
                    query = query.where(Post.forum_id.in_(forum_ids))

                # Query ready for execution (removed hint for compatibility)

                result = session.execute(query)
                posts = result.mappings().all()

                # Convert to list of dictionaries
                post_list = []
                for row in posts:
                    post_dict = dict(row)
                    # Add language hint if provided
                    if language_hint:
                        post_dict["language_hint"] = language_hint
                    post_list.append(post_dict)

                return post_list

        except SQLAlchemyError as e:
            print(f"Database error fetching unscored posts: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error fetching unscored posts: {e}")
            return []

    def save_sentiment_results(
        self,
        results: List[SentimentResult],
        batch_info: Optional[Dict[str, Any]] = None,
    ) -> Tuple[int, int]:
        """
        Save sentiment analysis results to the database.

        Args:
            results: List of SentimentResult objects
            batch_info: Optional batch metadata

        Returns:
            Tuple of (success_count, error_count)
        """
        if not results:
            return 0, 0

        success_count = 0
        error_count = 0

        try:
            with self.session_factory() as session:
                # Use transaction for atomicity
                with session.begin():
                    for result in results:
                        try:
                            if result.error:
                                # Log error and mark post as processed with null score to avoid reprocessing
                                print(
                                    f"Skipping post {result.post_id} due to error: {result.error}"
                                )
                                # Mark as processed with neutral score to prevent reprocessing
                                error_update_stmt = (
                                    update(Post)
                                    .where(Post.id == result.post_id)
                                    .values(
                                        sentiment_score=0.0,  # Neutral score for empty content
                                        sentiment_confidence=0.0,
                                        sentiment_language="unknown",
                                        sentiment_processed_at=func.now(),
                                        sentiment_processing_time=0.0,
                                    )
                                )
                                session.execute(error_update_stmt)
                                error_count += 1
                                continue

                            # Update post with sentiment score
                            update_stmt = (
                                update(Post)
                                .where(Post.id == result.post_id)
                                .values(
                                    sentiment_score=result.score,
                                    sentiment_confidence=result.confidence,
                                    sentiment_language=result.language,
                                    sentiment_processed_at=func.now(),
                                    sentiment_processing_time=result.processing_time,
                                )
                            )

                            # Execute update
                            update_result = session.execute(update_stmt)

                            if update_result.rowcount > 0:
                                success_count += 1
                            else:
                                print(f"No rows updated for post {result.post_id}")
                                error_count += 1

                        except Exception as e:
                            print(
                                f"Error saving sentiment for post {result.post_id}: {e}"
                            )
                            error_count += 1
                            continue

                    # Log batch information if provided
                    if batch_info and success_count > 0:
                        try:
                            # You could add batch-level logging here
                            # For example, insert into a processing_log table
                            pass
                        except Exception as e:
                            print(f"Warning: Could not log batch info: {e}")

                # Commit transaction
                session.commit()

        except SQLAlchemyError as e:
            print(f"Database transaction error: {e}")
            error_count = len(results)
            success_count = 0
        except Exception as e:
            print(f"Unexpected error saving sentiment results: {e}")
            error_count = len(results)
            success_count = 0

        return success_count, error_count

    def save_batch_results(
        self,
        batch_result: BatchInferenceResult,
        batch_metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[int, int]:
        """
        Save batch inference results to the database.

        Args:
            batch_result: BatchInferenceResult from sentiment analysis
            batch_metadata: Optional additional batch information

        Returns:
            Tuple of (success_count, error_count)
        """
        # Prepare batch metadata
        metadata = batch_metadata or {}
        metadata.update(
            {
                "batch_size": batch_result.batch_size,
                "processing_time": batch_result.processing_time,
                "processed_at": time.time(),
            }
        )

        return self.save_sentiment_results(batch_result.results, metadata)

    def get_sentiment_stats(
        self, days_back: int = 7, forum_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Get sentiment analysis statistics.

        Args:
            days_back: Number of days to look back
            forum_ids: Optional forum IDs to filter by

        Returns:
            Dictionary with sentiment statistics
        """
        try:
            with self.session_factory() as session:
                # Build base query
                query = select(
                    func.count(Post.id).label("total_posts"),
                    func.count(Post.sentiment_score).label("analyzed_posts"),
                    func.avg(Post.sentiment_score).label("avg_sentiment"),
                    func.min(Post.sentiment_score).label("min_sentiment"),
                    func.max(Post.sentiment_score).label("max_sentiment"),
                ).where(
                    Post.timestamp >= func.now() - func.interval(f"{days_back} days")
                )

                if forum_ids:
                    query = query.where(Post.forum_id.in_(forum_ids))

                result = session.execute(query).first()

                if result:
                    stats = dict(result)
                    stats["unanalyzed_posts"] = (
                        stats["total_posts"] - stats["analyzed_posts"]
                    )

                    if stats["total_posts"] > 0:
                        stats["analysis_coverage"] = (
                            stats["analyzed_posts"] / stats["total_posts"]
                        )
                    else:
                        stats["analysis_coverage"] = 0.0

                    return stats
                else:
                    return {
                        "total_posts": 0,
                        "analyzed_posts": 0,
                        "unanalyzed_posts": 0,
                        "avg_sentiment": None,
                        "min_sentiment": None,
                        "max_sentiment": None,
                        "analysis_coverage": 0.0,
                    }

        except Exception as e:
            print(f"Error getting sentiment stats: {e}")
            return {}

    def get_posts_needing_analysis(
        self, min_age_hours: int = 1, max_posts: int = 1000
    ) -> int:
        """
        Get count of posts that need sentiment analysis.

        Args:
            min_age_hours: Minimum age of posts in hours (to avoid very recent posts)
            max_posts: Maximum number of posts to consider

        Returns:
            Number of posts needing analysis
        """
        try:
            with self.session_factory() as session:
                query = (
                    select(func.count(Post.id))
                    .where(
                        and_(
                            Post.sentiment_score.is_(None),
                            Post.raw_text.is_not(None),
                            Post.raw_text != "",
                            Post.timestamp
                            <= func.now() - func.interval(f"{min_age_hours} hours"),
                        )
                    )
                    .limit(max_posts)
                )

                result = session.execute(query).scalar()
                return result or 0

        except Exception as e:
            print(f"Error counting posts needing analysis: {e}")
            return 0


# Convenience functions
def get_unscored_posts(
    session_factory: callable,
    limit: int = 100,
    language_hint: Optional[str] = None,
    forum_ids: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    """
    Convenience function to fetch unscored posts.

    Args:
        session_factory: Database session factory
        limit: Maximum number of posts to fetch
        language_hint: Optional language filter
        forum_ids: Optional forum IDs to filter by

    Returns:
        List of post dictionaries
    """
    handler = SentimentDBHandler(session_factory)
    return handler.fetch_unscored_posts(limit, language_hint, forum_ids)


def save_sentiment_scores(
    session_factory: callable,
    results: List[SentimentResult],
    batch_info: Optional[Dict[str, Any]] = None,
) -> Tuple[int, int]:
    """
    Convenience function to save sentiment results.

    Args:
        session_factory: Database session factory
        results: List of SentimentResult objects
        batch_info: Optional batch metadata

    Returns:
        Tuple of (success_count, error_count)
    """
    handler = SentimentDBHandler(session_factory)
    return handler.save_sentiment_results(results, batch_info)


def get_sentiment_statistics(
    session_factory: callable, days_back: int = 7, forum_ids: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Convenience function to get sentiment statistics.

    Args:
        session_factory: Database session factory
        days_back: Number of days to look back
        forum_ids: Optional forum IDs to filter by

    Returns:
        Dictionary with sentiment statistics
    """
    handler = SentimentDBHandler(session_factory)
    return handler.get_sentiment_stats(days_back, forum_ids)
