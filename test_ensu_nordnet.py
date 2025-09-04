#!/usr/bin/env python3
"""
ENSU Ticker Test for Nordnet Shareville Scraper

This script specifically tests the Nordnet scraper for the ENSU ticker
to verify it can correctly find and scrape posts from the ENSU page.
"""

import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from scraper.nordnet import NordnetScraper


def test_ensu_scraping():
    """Test ENSU ticker scraping specifically"""

    # Set up logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting ENSU ticker test for Nordnet scraper")

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

        # Print details of each post
        for i, post in enumerate(posts[:5]):  # Show first 5 posts
            logger.info(f"ENSU Post {i+1}:")
            logger.info(f"  Author: {post.author}")
            logger.info(f"  Ticker: {post.ticker}")
            logger.info(f"  Timestamp: {post.timestamp}")
            logger.info(f"  Content: {post.raw_text[:150]}...")
            logger.info(f"  URL: {post.url}")
            logger.info(f"  Metadata: {post.scraper_metadata}")
            logger.info("")

        # Test the ticker scraping method
        logger.info("Testing ticker scraping method for ENSU...")
        ticker_posts = scraper.scrape_ticker_posts("ENSU", max_pages=2)

        logger.info(f"Found {len(ticker_posts)} posts using ticker scraping method")

        # Verify that posts contain ENSU ticker
        ensu_posts = [
            post
            for post in ticker_posts
            if post.ticker and "ENSU" in post.ticker.upper()
        ]
        logger.info(
            f"Found {len(ensu_posts)} posts specifically mentioning ENSU ticker"
        )

        # Show some ENSU-specific posts
        for i, post in enumerate(ensu_posts[:3]):
            logger.info(f"ENSU-Specific Post {i+1}:")
            logger.info(f"  Author: {post.author}")
            logger.info(f"  Ticker: {post.ticker}")
            logger.info(f"  Content: {post.raw_text[:100]}...")
            logger.info("")

        # Test URL discovery
        logger.info("Testing URL discovery for ENSU...")

        # Check if ENSU is in known URLs
        if "ENSU" in scraper.ticker_urls:
            logger.info(f"ENSU found in known URLs: {scraper.ticker_urls['ENSU']}")
        else:
            logger.warning("ENSU not found in known URLs")

        # Test URL pattern matching
        logger.info("Testing URL pattern matching...")
        test_urls = [
            "https://www.nordnet.no/aksjer/kurser/ensu-xosl",
            "https://www.nordnet.no/aksjer/kurser/ensurge-micropower-ensu-xosl",
            "https://www.nordnet.no/aksjer/kurser/ensu",
        ]

        for test_url in test_urls:
            try:
                test_html = scraper.fetch(test_url)
                if test_html and "Shareville" in test_html:
                    logger.info(f"Working URL found: {test_url}")
                    break
                else:
                    logger.debug(f"URL not working: {test_url}")
            except Exception as e:
                logger.debug(f"URL failed: {test_url} - {e}")

        return True

    except Exception as e:
        logger.error(f"Error during ENSU testing: {e}")
        return False

    finally:
        scraper.close()


def test_ensu_persistence():
    """Test ENSU scraping through the persistence layer"""

    try:
        from scraper.persistence import ScraperPersistence

        logger = logging.getLogger(__name__)
        logger.info("Testing ENSU scraping through persistence layer...")

        with ScraperPersistence() as persistence:
            # Test specific ENSU scraping
            result = persistence.scrape_and_store_nordnet("ENSU", max_pages=1)

            logger.info(f"ENSU scraping result: {result}")

            if result.get("success"):
                logger.info(
                    f"Successfully scraped {result.get('posts_found', 0)} posts for ENSU"
                )
                logger.info(f"Stored {result.get('posts_stored', 0)} posts in database")
                return True
            else:
                logger.error(
                    f"ENSU scraping failed: {result.get('error', 'Unknown error')}"
                )
                return False

    except Exception as e:
        logger.error(f"Error testing persistence layer: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Testing ENSU ticker scraping on Nordnet Shareville")
    print("=" * 60)

    # Test basic scraping
    success1 = test_ensu_scraping()

    print("\n" + "=" * 60)

    # Test persistence layer
    success2 = test_ensu_persistence()

    print("\n" + "=" * 60)

    if success1 and success2:
        print("✅ ENSU ticker test completed successfully")
        print("✅ Both basic scraping and persistence layer tests passed")
    else:
        print("❌ ENSU ticker test failed")
        if not success1:
            print("❌ Basic scraping test failed")
        if not success2:
            print("❌ Persistence layer test failed")
        sys.exit(1)
