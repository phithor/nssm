#!/usr/bin/env python3
"""
Updated test script for Nordnet Shareville scraper

This script tests the Nordnet scraper with the correct HTML selectors
and verifies it can scrape both specific tickers and all stocks.
"""

import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from scraper.nordnet import NordnetScraper


def test_nordnet_scraper():
    """Test the Nordnet scraper with updated selectors"""

    # Set up logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting updated Nordnet scraper test")

    # Initialize scraper
    scraper = NordnetScraper(use_selenium_fallback=True)

    try:
        # Test URL for general Shareville posts
        test_urls = [
            "https://www.nordnet.no/aksjeforum",  # Main forum URL
            "https://www.nordnet.no/shareville",  # Alternative URL
        ]

        for test_url in test_urls:
            logger.info(f"Testing URL: {test_url}")

            # Fetch the page
            html = scraper.fetch(test_url)

            if html:
                logger.info(
                    f"Successfully fetched HTML content from {test_url} ({len(html)} characters)"
                )

                # Parse the HTML
                posts = scraper.parse(html)

                logger.info(f"Found {len(posts)} posts from {test_url}")

                # Print details of each post
                for i, post in enumerate(posts[:3]):  # Show first 3 posts
                    logger.info(f"Post {i+1}:")
                    logger.info(f"  Author: {post.author}")
                    logger.info(f"  Ticker: {post.ticker}")
                    logger.info(f"  Timestamp: {post.timestamp}")
                    logger.info(f"  Content: {post.raw_text[:100]}...")
                    logger.info(f"  URL: {post.url}")
                    logger.info(f"  Metadata: {post.scraper_metadata}")
                    logger.info("")
                break
            else:
                logger.warning(f"Failed to fetch HTML content from {test_url}")

        # Test ticker-specific scraping with known URLs
        logger.info("Testing ticker-specific scraping...")

        # Test ENSU (known URL)
        logger.info("Testing ENSU ticker...")
        ensu_posts = scraper.scrape_ticker_posts("ENSU", max_pages=1)
        logger.info(f"Found {len(ensu_posts)} posts for ENSU ticker")

        # Test NOVO (known URL)
        logger.info("Testing NOVO ticker...")
        novo_posts = scraper.scrape_ticker_posts("NOVO", max_pages=1)
        logger.info(f"Found {len(novo_posts)} posts for NOVO ticker")

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
        print("✅ Updated Nordnet scraper test completed successfully")
    else:
        print("❌ Updated Nordnet scraper test failed")
        sys.exit(1)
