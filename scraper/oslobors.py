#!/usr/bin/env python3
"""
Oslo Børs NewsWeb scraper for NSSM
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)


class OsloBorsScraper:
    """Scraper for Oslo Børs NewsWeb announcements"""

    def __init__(self):
        self.base_url = "https://newsweb.oslobors.no/"
        self.driver = None

    def setup_driver(self):
        """Setup Chrome driver with headless options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            return True
        except Exception as e:
            logger.error(f"Failed to create Chrome driver: {e}")
            return False

    def cleanup(self):
        """Clean up the web driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def fetch_latest_announcements(self, max_items: int = 50) -> List[Dict]:
        """
        Fetch the latest announcements from Oslo Børs NewsWeb

        Args:
            max_items: Maximum number of announcements to fetch

        Returns:
            List of announcement dictionaries
        """
        if not self.setup_driver():
            logger.error("Failed to setup web driver")
            return []

        try:
            logger.info(f"Fetching latest announcements from {self.base_url}")

            # Navigate to NewsWeb Oslo Børs
            self.driver.get(self.base_url)

            # Wait for page to load
            wait = WebDriverWait(self.driver, 30)
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.sc-hiDMwi"))
            )

            # Find the news table
            table = self.driver.find_element(By.CSS_SELECTOR, "table.sc-hiDMwi")

            # Find all table rows (skip header)
            rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
            logger.info(f"Found {len(rows)} announcements")

            # Extract data from rows
            announcements = []
            for i, row in enumerate(rows[:max_items]):
                try:
                    announcement = self._extract_announcement_from_row(row)
                    if announcement:
                        announcements.append(announcement)
                        logger.debug(
                            f"Extracted announcement {i+1}: "
                            f"{announcement['issuer_id']} - "
                            f"{announcement['title'][:50]}..."
                        )

                except Exception as e:
                    logger.error(f"Error extracting row {i}: {e}")
                    continue

            logger.info(f"Successfully extracted {len(announcements)} announcements")
            return announcements

        except Exception as e:
            logger.error(f"Error fetching announcements: {e}")
            return []
        finally:
            self.cleanup()

    def _extract_announcement_from_row(self, row) -> Optional[Dict]:
        """Extract announcement data from a table row"""
        try:
            # Extract columns
            cells = row.find_elements(By.CSS_SELECTOR, "td")
            if len(cells) < 7:
                return None

            date_time = cells[0].text.strip()
            market = cells[1].text.strip()
            issuer_id = cells[2].text.strip()

            # Get title from the link
            title_link = cells[3].find_element(By.CSS_SELECTOR, "a")
            title_text = title_link.text.strip()
            title_url = title_link.get_attribute("href")

            attachments = cells[5].text.strip()
            category = cells[6].text.strip()

            # Parse date
            try:
                parsed_date = datetime.strptime(date_time, "%d.%m.%Y %H:%M")
            except ValueError:
                parsed_date = None

            announcement = {
                "date_time": date_time,
                "parsed_date": parsed_date,
                "market": market,
                "issuer_id": issuer_id,
                "title": title_text,
                "url": title_url,
                "attachments_count": attachments if attachments else 0,
                "category": category,
                "source": "Oslo Børs NewsWeb",
            }

            return announcement

        except Exception as e:
            logger.error(f"Error extracting announcement from row: {e}")
            return None

    def fetch_announcement_details(self, announcement_url: str) -> Optional[Dict]:
        """
        Fetch detailed information for a specific announcement

        Args:
            announcement_url: URL of the announcement

        Returns:
            Dictionary with detailed announcement information
        """
        if not self.setup_driver():
            logger.error("Failed to setup web driver")
            return None

        try:
            logger.info(f"Fetching details for: {announcement_url}")

            # Navigate to the announcement page
            self.driver.get(announcement_url)
            time.sleep(3)

            # Extract detailed information
            details = {}

            # Check for error messages
            error_elements = self.driver.find_elements(
                By.CSS_SELECTOR, "div[role='alert']"
            )
            if error_elements:
                for error in error_elements:
                    error_text = error.text.strip()
                    if error_text:
                        logger.warning(f"Found error on page: {error_text}")

            # Extract header information
            try:
                # Get issuer name
                issuer_name = self.driver.find_element(
                    By.CSS_SELECTOR, "div.sc-hOzowv"
                ).text.strip()
                details["issuer_name"] = issuer_name

                # Get message details from the info grid
                info_items = self.driver.find_elements(By.CSS_SELECTOR, "div.sc-jTjUTQ")
                for item in info_items:
                    try:
                        label = item.find_element(
                            By.CSS_SELECTOR, "span.sc-dEVLtI"
                        ).text.strip()
                        value = item.find_element(
                            By.CSS_SELECTOR, "span.sc-brePNt"
                        ).text.strip()
                        details[label] = value
                    except Exception:
                        continue

            except Exception as e:
                logger.error(f"Error extracting header info: {e}")

            # Extract message title
            try:
                title_element = self.driver.find_element(
                    By.CSS_SELECTOR, "h1.sc-bhNKFk"
                )
                details["full_title"] = title_element.text.strip()
            except Exception:
                logger.warning("Could not extract full title")

            # Extract message content
            try:
                content_element = self.driver.find_element(
                    By.CSS_SELECTOR, "div[role='document']"
                )
                details["content"] = content_element.text.strip()
            except Exception:
                logger.warning("Could not extract content")

            # Extract attachments
            try:
                attachment_links = self.driver.find_elements(
                    By.CSS_SELECTOR, "a[download]"
                )
                attachments = []
                for link in attachment_links:
                    filename = link.get_attribute("download")
                    file_url = link.get_attribute("href")
                    attachments.append({"filename": filename, "url": file_url})
                details["attachments"] = attachments
            except Exception:
                logger.warning("Could not extract attachments")

            logger.info("Successfully extracted details for announcement")
            return details

        except Exception as e:
            logger.error(f"Error fetching announcement details: {e}")
            return None
        finally:
            self.cleanup()

    def search_announcements(
        self,
        issuer_id: str = None,
        title_search: str = None,
        from_date: datetime = None,
        to_date: datetime = None,
    ) -> List[Dict]:
        """
        Search for announcements using the search functionality

        Args:
            issuer_id: Specific issuer ID to search for
            title_search: Text to search in titles
            from_date: Start date for search
            to_date: End date for search

        Returns:
            List of matching announcements
        """
        if not self.setup_driver():
            logger.error("Failed to setup web driver")
            return []

        try:
            logger.info(
                f"Searching announcements with criteria: "
                f"issuer_id={issuer_id}, title_search={title_search}"
            )

            # Navigate to NewsWeb Oslo Børs
            self.driver.get(self.base_url)

            # Wait for page to load
            wait = WebDriverWait(self.driver, 30)
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='search']"))
            )

            # Fill in search criteria
            if issuer_id:
                # Find the issuer search input (React Select component)
                issuer_input = self.driver.find_element(
                    By.CSS_SELECTOR, "input[id*='react-select'][type='text']"
                )
                issuer_input.clear()
                issuer_input.send_keys(issuer_id)
                time.sleep(2)

                # Look for dropdown options and select first
                dropdown_options = self.driver.find_elements(
                    By.CSS_SELECTOR, "div[class*='option']"
                )
                if dropdown_options:
                    dropdown_options[0].click()
                    time.sleep(2)

            if title_search:
                # Find title search input
                title_input = self.driver.find_element(
                    By.CSS_SELECTOR, "input[name='messageTitle']"
                )
                title_input.clear()
                title_input.send_keys(title_search)

            # Submit search
            search_button = self.driver.find_element(
                By.CSS_SELECTOR, "button[type='submit']"
            )
            search_button.click()
            time.sleep(5)

            # Extract results
            try:
                results_table = self.driver.find_element(
                    By.CSS_SELECTOR, "table.sc-hiDMwi"
                )
                rows = results_table.find_elements(By.CSS_SELECTOR, "tbody tr")

                announcements = []
                for row in rows:
                    announcement = self._extract_announcement_from_row(row)
                    if announcement:
                        announcements.append(announcement)

                logger.info(f"Search returned {len(announcements)} results")
                return announcements

            except Exception:
                logger.warning("No results table found after search")
                return []

        except Exception as e:
            logger.error(f"Error searching announcements: {e}")
            return []
        finally:
            self.cleanup()

    def get_announcements_for_issuer(
        self, issuer_id: str, days_back: int = 7
    ) -> List[Dict]:
        """
        Get announcements for a specific issuer

        Args:
            issuer_id: The issuer ID to search for
            days_back: Number of days to look back

        Returns:
            List of announcements for the issuer
        """
        logger.info(
            f"Fetching announcements for issuer {issuer_id} (last {days_back} days)"
        )
        return self.search_announcements(issuer_id=issuer_id)
