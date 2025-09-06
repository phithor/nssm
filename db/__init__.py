"""
Database Models & Migrations Module

This module handles database connections, ORM models, and migrations
for the NSSM system using SQLAlchemy and supports both PostgreSQL and MySQL/MariaDB.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

__version__ = "0.1.0"
__author__ = "NSSM Team"

# Database configuration - supports both PostgreSQL and MySQL/MariaDB
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://nssm:MLxWMB%2F%40%2FWiFA%2FLq@192.168.0.90:3306/nssm",
)

# Create SQLAlchemy engine with connection pooling and timeout settings
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections every hour
    connect_args={
        "connect_timeout": 60,
        "read_timeout": 60,
        "write_timeout": 60,
    }
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()


# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_database_url():
    """Get the database URL for external modules."""
    return DATABASE_URL
