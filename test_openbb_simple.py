#!/usr/bin/env python3
"""
Simple test for OpenBB Yahoo Finance API call.
"""
import asyncio
from datetime import datetime

from openbb import obb


async def test_openbb_api():
    """Test basic OpenBB API call to Yahoo Finance."""
    print("🧪 Testing OpenBB Yahoo Finance API Call")
    print("=" * 50)

    try:
        # Simple synchronous call first
        print("Testing synchronous call...")
        result = obb.equity.price.historical(
            symbol="EQNR.OL",
            provider="yfinance",
            start_date="2024-01-01",
            end_date="2024-01-02",
        )
        print("✅ OpenBB synchronous API call successful!")
        print(f"Result type: {type(result)}")
        print(f"Result: {result}")
        return True

    except Exception as e:
        print(f"❌ OpenBB API call failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_openbb_api())
    exit(0 if result else 1)
