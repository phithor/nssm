"""
Shared Scraper Utilities

This module provides common utilities for all forum scrapers including
header randomization, polite delays, robots.txt compliance, and Selenium fallback.
"""

from .delay import polite_delay
from .headers import randomize_headers
from .robots import check_robots_txt

# Make SeleniumWrapper import optional to avoid import errors
try:
    from .selenium_wrapper import SeleniumWrapper

    __all__ = [
        "polite_delay",
        "randomize_headers",
        "check_robots_txt",
        "SeleniumWrapper",
    ]
except ImportError:
    SeleniumWrapper = None
    __all__ = ["polite_delay", "randomize_headers", "check_robots_txt"]
