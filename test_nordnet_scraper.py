#!/usr/bin/env python3
"""
Test script for Nordnet Shareville scraper

This script tests the Nordnet scraper with the ENSU ticker to verify
it can fetch and parse posts correctly.
"""

import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from scraper.nordnet import NordnetScraper


def test_nordnet_scraper():
    """Test the Nordnet scraper with ENSU ticker"""

    # Set up logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting Nordnet scraper test")

    # Initialize scraper
    scraper = NordnetScraper(use_selenium_fallback=True)

    try:
        # Test URL for ENSU ticker
        test_url = "https://www.nordnet.no/aksjer/kurser/ensurge-micropower-ensu-xosl"

        logger.info(f"Testing URL: {test_url}")

        # Fetch the page
        html = scraper.fetch(test_url)

        if not html:
            logger.error("Failed to fetch HTML content")
            return False

        logger.info(f"Successfully fetched HTML content ({len(html)} characters)")

        # Parse the HTML
        posts = scraper.parse(html)

        logger.info(f"Found {len(posts)} posts")

        # Print details of each post
        for i, post in enumerate(posts[:5]):  # Show first 5 posts
            logger.info(f"Post {i+1}:")
            logger.info(f"  Author: {post.author}")
            logger.info(f"  Ticker: {post.ticker}")
            logger.info(f"  Timestamp: {post.timestamp}")
            logger.info(f"  Content: {post.raw_text[:100]}...")
            logger.info(f"  URL: {post.url}")
            logger.info(f"  Metadata: {post.scraper_metadata}")
            logger.info("")

        # Test ticker-specific scraping
        logger.info("Testing ticker-specific scraping...")
        ticker_posts = scraper.scrape_ticker_posts("ENSU", max_pages=1)

        logger.info(f"Found {len(ticker_posts)} posts for ENSU ticker")

        # Test general scraping for all stocks
        logger.info("Testing general scraping for all stocks...")
        all_posts = scraper.scrape_all_posts(max_pages=1)

        logger.info(f"Found {len(all_posts)} posts for all stocks")

        return True

    except Exception as e:
        logger.error(f"Error during testing: {e}")
        return False

    finally:
        scraper.close()


if __name__ == "__main__":
    success = test_nordnet_scraper()
    if success:
        print("✅ Nordnet scraper test completed successfully")
    else:
        print("❌ Nordnet scraper test failed")
        sys.exit(1)
