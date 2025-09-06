"""
Database initialization script for NSSM

This script initializes the database by creating tables and running migrations.
"""

import logging
import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import after path setup - this is necessary for the script to work
try:
    from db import Base, engine
except ImportError:
    # Fallback for when running as module
    import db

    Base = db.Base
    engine = db.engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_tables():
    """Create all tables using SQLAlchemy"""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")
        raise


def run_migrations():
    """Run Alembic migrations"""
    try:
        logger.info("Running database migrations...")

        # Get the project root directory
        project_root = Path(__file__).parent.parent

        # Create Alembic configuration
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", str(project_root / "alembic"))
        alembic_cfg.set_main_option(
            "sqlalchemy.url",
            os.getenv(
                "DATABASE_URL",
                "postgresql://nssm_user:nssm_password@localhost:5432/nssm_db",
            ),
        )

        # Run migrations
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Database migrations completed successfully")

    except Exception as e:
        logger.error(f"❌ Error running migrations: {e}")
        raise


def verify_database():
    """Verify that the database is properly set up"""
    try:
        logger.info("Verifying database setup...")

        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT VERSION()"))
            version = result.fetchone()[0]
            logger.info(f"Database version: {version}")

        # Check if tables exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        expected_tables = ["forums", "posts", "sentiment_agg", "alerts"]

        for table in expected_tables:
            if table in tables:
                logger.info(f"✅ Table '{table}' exists")
            else:
                logger.warning(f"⚠️ Table '{table}' not found")

        # Note: TimescaleDB check skipped for MySQL/MariaDB compatibility
        logger.info("✅ Database verification supports MySQL/MariaDB")

        logger.info("✅ Database verification completed")

    except Exception as e:
        logger.error(f"❌ Error verifying database: {e}")
        raise


def init_database():
    """Initialize database - alias for main() for backward compatibility"""
    main()


def main():
    """Main initialization function"""
    logger.info("🚀 Starting NSSM database initialization...")

    try:
        # Run migrations (migrations handle table creation idempotently)
        run_migrations()

        # Verify setup
        verify_database()

        logger.info("🎉 Database initialization completed successfully!")

    except Exception as e:
        logger.error(f"💥 Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
