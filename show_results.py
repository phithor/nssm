import asyncio

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from db.models import Base, MarketPrice
from market.data import fetch_openbb_prices


async def main():
    # Create persistent database for testing
    test_db = "market_results.db"
    engine = create_engine(f"sqlite:///{test_db}")
    Base.metadata.create_all(engine)

    print("🧪 OpenBB Market Price Data Integration Test")
    print("=" * 50)

    try:
        # Fetch price data
        results = await fetch_openbb_prices(
            db_url=f"sqlite:///{test_db}", tickers=["EQNR"], days_back=1
        )

        print(f"✅ Fetch Results: {results}")

        # Query and display stored data
        SessionLocal = sessionmaker(bind=engine)
        with SessionLocal() as session:
            # Count records
            count = session.execute(
                select(func.count(MarketPrice.id)).where(MarketPrice.ticker == "EQNR")
            ).scalar()

            print(f"📊 Total Records Stored: {count}")

            if count > 0:
                print("\n📈 Sample Price Records:")
                print("-" * 40)

                # Get sample records
                records = (
                    session.execute(
                        select(MarketPrice)
                        .where(MarketPrice.ticker == "EQNR")
                        .order_by(MarketPrice.timestamp)
                        .limit(5)
                    )
                    .scalars()
                    .all()
                )

                for i, record in enumerate(records, 1):
                    print(
                        f"{i}. {record.timestamp.strftime('%Y-%m-%d %H:%M')} - ${record.price:.2f} "
                        f"(High: ${record.high:.2f}, Low: ${record.low:.2f}, Vol: {record.volume})"
                    )

                # Show date range
                min_date = session.execute(
                    select(func.min(MarketPrice.timestamp)).where(
                        MarketPrice.ticker == "EQNR"
                    )
                ).scalar()

                max_date = session.execute(
                    select(func.max(MarketPrice.timestamp)).where(
                        MarketPrice.ticker == "EQNR"
                    )
                ).scalar()

                print(f"\n📅 Date Range: {min_date} to {max_date}")

        print(f"\n�� Database saved to: {test_db}")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
