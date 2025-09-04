"""
Configuration Management Module

This module handles environment variables, configuration files,
and settings for the NSSM system.
"""

__version__ = "0.1.0"
__author__ = "NSSM Team"

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


def load_markets_config() -> Dict[str, Any]:
    """
    Load markets configuration from markets.yml.

    Returns:
        Dictionary containing market configuration data
    """
    config_path = Path(__file__).parent / "markets.yml"

    if not config_path.exists():
        raise FileNotFoundError(f"Markets configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_database_url() -> str:
    """Get database URL from environment variables."""
    return os.getenv("DATABASE_URL", "mysql+pymysql://nssm:MLxWMB/@/WiFA/Lq@192.168.0.90:3306/nssm")


def get_openbb_api_key() -> Optional[str]:
    """Get OpenBB API key from environment."""
    return os.getenv("OPENBB_API_KEY")


def get_prometheus_pushgateway_url() -> Optional[str]:
    """Get Prometheus pushgateway URL from environment."""
    return os.getenv("PROM_PUSHGATEWAY")


def is_production() -> bool:
    """Check if running in production environment."""
    return os.getenv("ENVIRONMENT", "development").lower() == "production"
