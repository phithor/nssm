"""
Selenium Wrapper Utility

Provides a fallback wrapper for Selenium when JavaScript rendering is required.
This is used when requests+BeautifulSoup cannot handle dynamic content.
"""

import logging
from typing import TYPE_CHECKING, Optional, Union

try:
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


if TYPE_CHECKING:
    from selenium.webdriver.chrome.webdriver import Chrome as ChromeDriver


class SeleniumWrapper:
    """
    Wrapper for Selenium WebDriver to handle JavaScript-rendered content.

    This is used as a fallback when requests+BeautifulSoup cannot
    extract the required data from a page.
    """

    def __init__(
        self,
        headless: bool = True,
        user_agent: Optional[str] = None,
        timeout: int = 30,
        implicit_wait: int = 10,
    ):
        """
        Initialize the Selenium wrapper.

        Args:
            headless: Run browser in headless mode
            user_agent: Custom user agent string
            timeout: Page load timeout in seconds
            implicit_wait: Implicit wait time in seconds
        """
        self.headless = headless
        self.user_agent = user_agent
        self.timeout = timeout
        self.implicit_wait = implicit_wait
        self.driver: Optional["ChromeDriver"] = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        if not SELENIUM_AVAILABLE:
            self.logger.warning(
                "Selenium not available. Install selenium package to use this feature."
            )

    def _create_driver(self) -> Optional["ChromeDriver"]:
        """Create and configure Chrome WebDriver."""
        if not SELENIUM_AVAILABLE:
            return None

        try:
            options = Options()

            if self.headless:
                options.add_argument("--headless")

            # Add user agent if specified
            if self.user_agent:
                options.add_argument(f"--user-agent={self.user_agent}")

            # Additional options for stability
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)

            # Create driver
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(self.timeout)
            driver.implicitly_wait(self.implicit_wait)

            # Execute script to remove webdriver property
            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            return driver
        except Exception as e:
            self.logger.error(f"Failed to create Chrome driver: {e}")
            return None

    def get_page_source(self, url: str) -> Optional[str]:
        """
        Get the page source using Selenium.

        Args:
            url: URL to fetch

        Returns:
            Page HTML content or None if failed
        """
        if not SELENIUM_AVAILABLE:
            self.logger.error("Selenium not available")
            return None

        try:
            if not self.driver:
                self.driver = self._create_driver()
                if not self.driver:
                    return None

            self.logger.info(f"Fetching {url} with Selenium")
            self.driver.get(url)

            # Wait for page to load
            if SELENIUM_AVAILABLE:
                WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

            # Get page source
            page_source = self.driver.page_source
            self.logger.info(f"Successfully fetched {url} with Selenium")

            return page_source

        except TimeoutException:
            self.logger.error(f"Timeout waiting for page to load: {url}")
            return None
        except WebDriverException as e:
            self.logger.error(f"WebDriver error for {url}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error fetching {url}: {e}")
            return None

    def wait_for_element(
        self,
        selector: str,
        by: Union[str, "By"] = By.CSS_SELECTOR,
        timeout: Optional[int] = None,
    ) -> bool:
        """
        Wait for a specific element to appear on the page.

        Args:
            selector: Element selector
            by: Method to find element (default: CSS_SELECTOR)
            timeout: Custom timeout in seconds

        Returns:
            True if element found, False otherwise
        """
        if not self.driver or not SELENIUM_AVAILABLE:
            return False

        try:
            wait_timeout = timeout or self.timeout
            WebDriverWait(self.driver, wait_timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return True
        except TimeoutException:
            self.logger.warning(f"Element not found within timeout: {selector}")
            return False

    def close(self):
        """Close the WebDriver and clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.error(f"Error closing driver: {e}")
            finally:
                self.driver = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def __del__(self):
        """Cleanup on deletion."""
        self.close()


def is_selenium_available() -> bool:
    """Check if Selenium is available in the environment."""
    return SELENIUM_AVAILABLE
