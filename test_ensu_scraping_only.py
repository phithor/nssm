#!/usr/bin/env python3
"""
ENSU Scraping Test (No Database)

This script tests only the scraping functionality for ENSU ticker
without requiring database connection.
"""

import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from scraper.nordnet import NordnetScraper


def test_ensu_scraping_only():
    """Test ENSU ticker scraping without database"""

    # Set up logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting ENSU scraping test (no database)")

    # Initialize scraper
    scraper = NordnetScraper(use_selenium_fallback=True)

    try:
        # Test the known ENSU URL directly
        ensu_url = "https://www.nordnet.no/aksjer/kurser/ensurge-micropower-ensu-xosl"
        logger.info(f"Testing ENSU URL: {ensu_url}")

        # Fetch the page
        html = scraper.fetch(ensu_url)

        if not html:
            logger.error("Failed to fetch HTML content from ENSU URL")
            return False

        logger.info(f"Successfully fetched HTML content ({len(html)} characters)")

        # Check if Shareville content is present
        if "Shareville" not in html:
            logger.warning("Shareville content not found in HTML")
            return False

        logger.info("Shareville content found in HTML")

        # Parse the HTML
        posts = scraper.parse(html)

        logger.info(f"Found {len(posts)} posts from ENSU page")

        # Filter for actual forum posts (not navigation items)
        forum_posts = []
        navigation_keywords = [
            "børsen i dag",
            "nyheter",
            "shareville",
            "aksjekurser",
            "etf-liste",
            "etf-inspirasjon",
            "aksje- og fondskonto",
        ]

        for post in posts:
            # Skip navigation items
            if any(keyword in post.author.lower() for keyword in navigation_keywords):
                continue
            if any(keyword in post.raw_text.lower() for keyword in navigation_keywords):
                continue
            forum_posts.append(post)

        logger.info(
            f"Found {len(forum_posts)} actual forum posts (excluding navigation)"
        )

        # Print details of actual forum posts
        for i, post in enumerate(forum_posts[:10]):  # Show first 10 forum posts
            logger.info(f"ENSU Forum Post {i+1}:")
            logger.info(f"  Author: {post.author}")
            logger.info(f"  Ticker: {post.ticker}")
            logger.info(f"  Timestamp: {post.timestamp}")
            logger.info(f"  Content: {post.raw_text[:200]}...")
            logger.info(f"  URL: {post.url}")
            logger.info("")

        # Test the ticker scraping method
        logger.info("Testing ticker scraping method for ENSU...")
        ticker_posts = scraper.scrape_ticker_posts("ENSU", max_pages=1)

        logger.info(f"Found {len(ticker_posts)} posts using ticker scraping method")

        # Filter ticker posts for actual forum content
        forum_ticker_posts = []
        for post in ticker_posts:
            if any(keyword in post.author.lower() for keyword in navigation_keywords):
                continue
            if any(keyword in post.raw_text.lower() for keyword in navigation_keywords):
                continue
            forum_ticker_posts.append(post)

        logger.info(
            f"Found {len(forum_ticker_posts)} actual forum posts from ticker method"
        )

        # Show some actual forum posts
        for i, post in enumerate(forum_ticker_posts[:5]):
            logger.info(f"Actual Forum Post {i+1}:")
            logger.info(f"  Author: {post.author}")
            logger.info(f"  Ticker: {post.ticker}")
            logger.info(f"  Content: {post.raw_text[:150]}...")
            logger.info("")

        # Test URL discovery
        logger.info("Testing URL discovery for ENSU...")

        # Check if ENSU is in known URLs
        if "ENSU" in scraper.ticker_urls:
            logger.info(f"ENSU found in known URLs: {scraper.ticker_urls['ENSU']}")
        else:
            logger.warning("ENSU not found in known URLs")

        return True

    except Exception as e:
        logger.error(f"Error during ENSU testing: {e}")
        return False

    finally:
        scraper.close()


if __name__ == "__main__":
    print("🧪 Testing ENSU ticker scraping (no database)")
    print("=" * 60)

    success = test_ensu_scraping_only()

    print("\n" + "=" * 60)

    if success:
        print("✅ ENSU scraping test completed successfully")
        print("✅ Scraper is working correctly for ENSU ticker")
    else:
        print("❌ ENSU scraping test failed")
        sys.exit(1)
