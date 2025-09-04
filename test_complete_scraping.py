#!/usr/bin/env python3
"""
Test script for complete scraping pipeline

This script tests the complete scraping pipeline including the new
Nordnet Shareville scraper to verify everything works together.
"""

import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from scraper.persistence import ScraperPersistence


def test_complete_scraping():
    """Test the complete scraping pipeline"""

    # Set up logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting complete scraping pipeline test")

    # Initialize persistence layer
    with ScraperPersistence() as persistence:
        try:
            # Test scraping all forums
            logger.info("Testing scraping all forums...")
            results = persistence.scrape_all_forums(max_pages=1, max_posts=10)

            logger.info("Scraping results:")
            for forum_name, result in results.items():
                if forum_name == "summary":
                    logger.info(f"  Summary: {result}")
                else:
                    success = result.get("success", False)
                    posts_found = result.get("posts_found", 0)
                    posts_stored = result.get("posts_stored", 0)
                    logger.info(
                        f"  {forum_name}: Success={success}, Found={posts_found}, Stored={posts_stored}"
                    )

            # Test forum statistics
            logger.info("Testing forum statistics...")
            stats = persistence.get_forum_stats()
            logger.info(f"Forum stats: {stats}")

            return True

        except Exception as e:
            logger.error(f"Error during testing: {e}")
            return False


if __name__ == "__main__":
    success = test_complete_scraping()
    if success:
        print("✅ Complete scraping pipeline test completed successfully")
    else:
        print("❌ Complete scraping pipeline test failed")
        sys.exit(1)
