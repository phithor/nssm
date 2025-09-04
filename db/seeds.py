"""
Database seeder script for NSSM

This script populates the database with sample data for development and testing.
"""

import random
from datetime import datetime, timedelta

from . import SessionLocal
from .models import Alert, Forum, Post, SentimentAgg


def seed_forums():
    """Seed sample forums"""
    forums_data = [
        {"name": "Seeking Alpha", "url": "https://seekingalpha.com"},
        {"name": "Yahoo Finance", "url": "https://finance.yahoo.com"},
        {"name": "Hegnar Online", "url": "https://www.finansavisen.no/forum/"},
        {"name": "Placera Forum", "url": "https://forum.placera.se/upptack"},
    ]

    db = SessionLocal()
    try:
        for forum_data in forums_data:
            forum = Forum(**forum_data)
            db.add(forum)
        db.commit()
        print(f"✅ Seeded {len(forums_data)} forums")
    except Exception as e:
        print(f"❌ Error seeding forums: {e}")
        db.rollback()
    finally:
        db.close()


def seed_sample_posts():
    """Seed sample posts with sentiment scores"""
    db = SessionLocal()
    try:
        # Get forum IDs
        forums = db.query(Forum).all()
        if not forums:
            print("❌ No forums found. Run seed_forums() first.")
            return

        tickers = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "NVDA", "META", "NFLX"]
        sample_texts = [
            "This stock is going to the moon! 🚀",
            "I'm bullish on this company's future prospects.",
            "Not sure about this one, seems risky.",
            "Great earnings report, very positive outlook.",
            "This is a terrible investment, avoid at all costs.",
            "Solid fundamentals, good long-term play.",
            "Market sentiment is turning bearish on this.",
            "Innovation pipeline looks promising.",
        ]

        posts_data = []
        for i in range(50):  # Create 50 sample posts
            forum = random.choice(forums)
            ticker = random.choice(tickers)
            text = random.choice(sample_texts)

            # Generate sentiment score based on text content
            if (
                "moon" in text.lower()
                or "bullish" in text.lower()
                or "positive" in text.lower()
            ):
                sentiment = random.uniform(0.6, 1.0)
            elif (
                "terrible" in text.lower()
                or "avoid" in text.lower()
                or "bearish" in text.lower()
            ):
                sentiment = random.uniform(-1.0, -0.4)
            else:
                sentiment = random.uniform(-0.3, 0.5)

            post = Post(
                forum_id=forum.id,
                ticker=ticker,
                timestamp=datetime.now() - timedelta(hours=random.randint(1, 168)),
                author=f"user_{random.randint(1000, 9999)}",
                raw_text=text,
                clean_text=text,
                sentiment_score=sentiment,
            )
            posts_data.append(post)

        db.add_all(posts_data)
        db.commit()
        print(f"✅ Seeded {len(posts_data)} sample posts")

    except Exception as e:
        print(f"❌ Error seeding posts: {e}")
        db.rollback()
    finally:
        db.close()


def seed_sample_sentiment_agg():
    """Seed sample sentiment aggregation data"""
    db = SessionLocal()
    try:
        # Get some posts to aggregate
        posts = db.query(Post).filter(Post.sentiment_score.isnot(None)).limit(100).all()
        if not posts:
            print(
                "❌ No posts with sentiment scores found. Run seed_sample_posts() first."
            )
            return

        # Group posts by ticker and time intervals
        ticker_groups = {}
        for post in posts:
            if post.ticker not in ticker_groups:
                ticker_groups[post.ticker] = []
            ticker_groups[post.ticker].append(post)

        agg_data = []
        for ticker, ticker_posts in ticker_groups.items():
            # Create daily aggregations for the last 7 days
            for days_ago in range(7):
                date = datetime.now().date() - timedelta(days=days_ago)
                start_time = datetime.combine(date, datetime.min.time())
                end_time = datetime.combine(date, datetime.max.time())

                # Filter posts for this date
                day_posts = [p for p in ticker_posts if p.timestamp.date() == date]

                if day_posts:
                    avg_score = sum(p.sentiment_score for p in day_posts) / len(
                        day_posts
                    )
                    agg = SentimentAgg(
                        ticker=ticker,
                        interval_start=start_time,
                        interval_end=end_time,
                        avg_score=avg_score,
                        post_cnt=len(day_posts),
                    )
                    agg_data.append(agg)

        db.add_all(agg_data)
        db.commit()
        print(f"✅ Seeded {len(agg_data)} sentiment aggregation records")

    except Exception as e:
        print(f"❌ Error seeding sentiment aggregation: {e}")
        db.rollback()
    finally:
        db.close()


def seed_sample_alerts():
    """Seed sample alerts"""
    db = SessionLocal()
    try:
        tickers = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
        alert_rules = [
            "Sentiment score > 0.8",
            "Sentiment score < -0.8",
            "High post volume (>100 posts/day)",
            "Rapid sentiment change (>0.5 in 1 hour)",
            "Crossed moving average threshold",
        ]

        alerts_data = []
        for i in range(10):
            alert = Alert(
                ticker=random.choice(tickers),
                rule=random.choice(alert_rules),
                triggered_at=datetime.now() - timedelta(hours=random.randint(1, 72)),
                is_active=random.choice([True, False]),
            )
            alerts_data.append(alert)

        db.add_all(alerts_data)
        db.commit()
        print(f"✅ Seeded {len(alerts_data)} sample alerts")

    except Exception as e:
        print(f"❌ Error seeding alerts: {e}")
        db.rollback()
    finally:
        db.close()


def run_all_seeds():
    """Run all seed functions in order"""
    print("🌱 Starting database seeding...")

    seed_forums()
    seed_sample_posts()
    seed_sample_sentiment_agg()
    seed_sample_alerts()

    print("✅ Database seeding completed!")


if __name__ == "__main__":
    run_all_seeds()
