"""
News State Management

This module manages incremental state for news fetching to avoid duplicate downloads
and enable efficient backfilling. Tracks last fetch timestamps per source.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

import pytz

logger = logging.getLogger(__name__)


class NewsStateManager:
    """Manages state for incremental news fetching."""

    def __init__(self, cache_dir: str = "cache"):
        """Initialize state manager with cache directory."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.state_file = self.cache_dir / "news_state.json"
        self.oslo_tz = pytz.timezone("Europe/Oslo")

    def load_state(self) -> Dict[str, Any]:
        """Load current state from JSON file."""
        if not self.state_file.exists():
            return self._create_default_state()

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            # Convert timestamp strings back to datetime objects
            for source, source_state in state.get("sources", {}).items():
                if "last_fetch_ts" in source_state and source_state["last_fetch_ts"]:
                    try:
                        # Parse ISO format timestamp
                        dt = datetime.fromisoformat(source_state["last_fetch_ts"])
                        if dt.tzinfo is None:
                            dt = self.oslo_tz.localize(dt)
                        source_state["last_fetch_ts"] = dt
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to parse timestamp for {source}: {e}")
                        source_state["last_fetch_ts"] = None

            return state

        except Exception as e:
            logger.error(f"Failed to load state file: {e}")
            return self._create_default_state()

    def _create_default_state(self) -> Dict[str, Any]:
        """Create default state structure."""
        return {
            "version": "1.0",
            "last_updated": datetime.now(self.oslo_tz).isoformat(),
            "sources": {
                "openbb": {
                    "last_fetch_ts": None,
                    "total_fetches": 0,
                    "last_backfill_ts": None,
                },
                "oslobors": {
                    "last_fetch_ts": None,
                    "total_fetches": 0,
                    "last_backfill_ts": None,
                },
                "nasdaq_sto": {
                    "last_fetch_ts": None,
                    "total_fetches": 0,
                    "last_backfill_ts": None,
                },
                "nasdaq_cph": {
                    "last_fetch_ts": None,
                    "total_fetches": 0,
                    "last_backfill_ts": None,
                },
                "nasdaq_hex": {
                    "last_fetch_ts": None,
                    "total_fetches": 0,
                    "last_backfill_ts": None,
                },
            },
        }

    def save_state(self, state: Dict[str, Any]) -> None:
        """Save state to JSON file."""
        try:
            # Convert datetime objects to ISO strings for JSON serialization
            serializable_state = self._make_serializable(state)

            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(serializable_state, f, indent=2, ensure_ascii=False)

            logger.debug("State saved successfully")

        except Exception as e:
            logger.error(f"Failed to save state file: {e}")

    def _make_serializable(self, obj: Any) -> Any:
        """Convert datetime objects to ISO strings for JSON serialization."""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj

    def get_last_fetch_timestamp(self, source: str) -> Optional[datetime]:
        """Get the last fetch timestamp for a source."""
        state = self.load_state()
        source_state = state.get("sources", {}).get(source, {})
        return source_state.get("last_fetch_ts")

    def update_last_fetch_timestamp(
        self, source: str, timestamp: Optional[datetime] = None
    ) -> None:
        """Update the last fetch timestamp for a source."""
        if timestamp is None:
            timestamp = datetime.now(self.oslo_tz)

        state = self.load_state()
        if source not in state["sources"]:
            state["sources"][source] = {
                "last_fetch_ts": None,
                "total_fetches": 0,
                "last_backfill_ts": None,
            }

        state["sources"][source]["last_fetch_ts"] = timestamp
        state["sources"][source]["total_fetches"] += 1
        state["last_updated"] = datetime.now(self.oslo_tz).isoformat()

        self.save_state(state)
        logger.debug(f"Updated last fetch timestamp for {source}: {timestamp}")

    def should_backfill(self, source: str, backfill_threshold_hours: int = 48) -> bool:
        """Check if backfill is needed for a source."""
        last_backfill = self.get_last_backfill_timestamp(source)

        if last_backfill is None:
            return True

        now = datetime.now(self.oslo_tz)
        time_since_backfill = now - last_backfill

        return time_since_backfill.total_seconds() > (backfill_threshold_hours * 3600)

    def get_last_backfill_timestamp(self, source: str) -> Optional[datetime]:
        """Get the last backfill timestamp for a source."""
        state = self.load_state()
        source_state = state.get("sources", {}).get(source, {})
        return source_state.get("last_backfill_ts")

    def update_last_backfill_timestamp(
        self, source: str, timestamp: Optional[datetime] = None
    ) -> None:
        """Update the last backfill timestamp for a source."""
        if timestamp is None:
            timestamp = datetime.now(self.oslo_tz)

        state = self.load_state()
        if source not in state["sources"]:
            state["sources"][source] = {
                "last_fetch_ts": None,
                "total_fetches": 0,
                "last_backfill_ts": None,
            }

        state["sources"][source]["last_backfill_ts"] = timestamp
        state["last_updated"] = datetime.now(self.oslo_tz).isoformat()

        self.save_state(state)
        logger.debug(f"Updated last backfill timestamp for {source}: {timestamp}")

    def get_incremental_fetch_params(
        self, source: str, default_days_back: int = 1
    ) -> Dict[str, Any]:
        """Get parameters for incremental fetching."""
        last_fetch = self.get_last_fetch_timestamp(source)

        if last_fetch is None:
            # First time fetching - use default days back
            return {"days_back": default_days_back, "is_incremental": False}

        now = datetime.now(self.oslo_tz)
        time_since_last_fetch = now - last_fetch

        # If last fetch was more than 48 hours ago, do a longer backfill
        if time_since_last_fetch.total_seconds() > (48 * 3600):
            days_back = min(
                int(time_since_last_fetch.total_seconds() / (24 * 3600)), 30
            )  # Max 30 days
            return {
                "days_back": days_back,
                "is_incremental": False,
                "last_fetch": last_fetch,
            }

        # Normal incremental fetch
        days_back = max(1, int(time_since_last_fetch.total_seconds() / (24 * 3600)))
        return {
            "days_back": days_back,
            "is_incremental": True,
            "last_fetch": last_fetch,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the state."""
        state = self.load_state()

        stats = {
            "total_sources": len(state.get("sources", {})),
            "last_updated": state.get("last_updated"),
            "source_stats": {},
        }

        for source, source_state in state.get("sources", {}).items():
            stats["source_stats"][source] = {
                "total_fetches": source_state.get("total_fetches", 0),
                "has_last_fetch": source_state.get("last_fetch_ts") is not None,
                "has_last_backfill": source_state.get("last_backfill_ts") is not None,
            }

        return stats

    def reset_source(self, source: str) -> None:
        """Reset state for a specific source."""
        state = self.load_state()
        if source in state["sources"]:
            state["sources"][source] = {
                "last_fetch_ts": None,
                "total_fetches": 0,
                "last_backfill_ts": None,
            }
            state["last_updated"] = datetime.now(self.oslo_tz).isoformat()
            self.save_state(state)
            logger.info(f"Reset state for source: {source}")

    def reset_all(self) -> None:
        """Reset all state."""
        state = self._create_default_state()
        self.save_state(state)
        logger.info("Reset all state")


# Convenience functions
def get_state_manager(cache_dir: str = "cache") -> NewsStateManager:
    """Get a NewsStateManager instance."""
    return NewsStateManager(cache_dir)


def should_fetch_source(source: str, cache_dir: str = "cache") -> bool:
    """Check if a source should be fetched based on last fetch time."""
    manager = get_state_manager(cache_dir)
    last_fetch = manager.get_last_fetch_timestamp(source)

    if last_fetch is None:
        return True

    now = datetime.now(pytz.timezone("Europe/Oslo"))
    time_since_fetch = now - last_fetch

    # Fetch if more than 1 hour has passed
    return time_since_fetch.total_seconds() > 3600


def update_source_fetch_time(source: str, cache_dir: str = "cache") -> None:
    """Update the last fetch time for a source."""
    manager = get_state_manager(cache_dir)
    manager.update_last_fetch_timestamp(source)
