"""
Database Models & Migrations Module

This module handles database connections, ORM models, and migrations
for the NSSM system using SQLAlchemy and PostgreSQL.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

__version__ = "0.1.0"
__author__ = "NSSM Team"

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://nssm_user:nssm_password@localhost:5432/nssm_db"
)

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL, echo=False)

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
