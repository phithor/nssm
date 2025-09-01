"""
NSSM Analytics Scheduler

Runs sentiment aggregation and anomaly detection on an hourly schedule.
Designed to run as a background service for continuous analytics processing.
"""

import logging
import signal
import sys
import time

import schedule

from .aggregator import SentimentAggregator


class AnalyticsScheduler:
    """Scheduler for running analytics pipelines at regular intervals."""

    def __init__(self):
        self.aggregator = SentimentAggregator()
        self.running = False
        self.logger = logging.getLogger(__name__)

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def run_hourly_analytics(self):
        """Run the complete analytics pipeline (aggregation + anomaly detection)."""
        try:
            self.logger.info("🕐 Starting scheduled analytics run...")

            # Run combined pipeline
            result = self.aggregator.run_aggregation_pipeline(
                hours_back=24, window_minutes=5, min_confidence=0.5
            )

            if result["success"]:
                self.logger.info(
                    f"✅ Aggregation completed: {result['aggregates_persisted']} aggregates persisted"
                )
            else:
                self.logger.error(f"❌ Aggregation failed: {result['error']}")
                return

            # Run anomaly detection
            anomaly_result = self.aggregator.run_anomaly_detection_pipeline(
                hours_back=24, zscore_threshold=2.0, min_post_count=5
            )

            if anomaly_result["success"]:
                self.logger.info(
                    f"✅ Anomaly detection completed: {anomaly_result['anomalies_persisted']} anomalies detected"
                )
            else:
                self.logger.error(
                    f"❌ Anomaly detection failed: {anomaly_result['error']}"
                )

        except Exception as e:
            self.logger.error(f"💥 Scheduled analytics run failed: {e}")

    def run_daily_maintenance(self):
        """Run daily maintenance tasks."""
        try:
            self.logger.info("🧹 Starting daily maintenance...")

            # Could add tasks like:
            # - Cleaning old aggregates
            # - Database optimization
            # - Performance monitoring

            self.logger.info("✅ Daily maintenance completed")

        except Exception as e:
            self.logger.error(f"💥 Daily maintenance failed: {e}")

    def start(self):
        """Start the scheduler service."""
        self.logger.info("🚀 Starting NSSM Analytics Scheduler...")

        # Schedule hourly analytics
        schedule.every().hour.at(":00").do(self.run_hourly_analytics)

        # Schedule daily maintenance at 2 AM
        schedule.every().day.at("02:00").do(self.run_daily_maintenance)

        self.running = True
        self.logger.info("📅 Scheduled jobs:")
        for job in schedule.jobs:
            self.logger.info(f"   {job}")

        try:
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            self.logger.info("⏹️  Scheduler stopped by user")
        except Exception as e:
            self.logger.error(f"💥 Scheduler error: {e}")
        finally:
            self.logger.info("👋 NSSM Analytics Scheduler stopped")

    def stop(self):
        """Stop the scheduler service."""
        self.running = False
        self.logger.info("🛑 Stopping scheduler...")


def main():
    """Main entry point for the scheduler service."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("analytics_scheduler.log"),
        ],
    )

    logger = logging.getLogger(__name__)

    try:
        logger.info("🌟 NSSM Analytics Scheduler starting...")
        scheduler = AnalyticsScheduler()
        scheduler.start()
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
