# NSSM Database Module

This module provides the database layer for the NSSM (Neural Sentiment Stock Monitor) system using SQLAlchemy ORM and PostgreSQL with TimescaleDB extension.

## Overview

The database schema consists of four main tables:

1. **`forums`** - Financial discussion forums (Reddit, StockTwits, etc.)
2. **`posts`** - Individual forum posts with sentiment analysis
3. **`sentiment_agg`** - Time-series sentiment aggregation using TimescaleDB
4. **`alerts`** - Trading alerts based on sentiment triggers

## Features

- **SQLAlchemy ORM** for type-safe database operations
- **Alembic migrations** for schema versioning
- **TimescaleDB integration** for time-series data optimization
- **Comprehensive indexing** for fast queries
- **Relationship management** between entities
- **Sample data seeding** for development and testing

## Quick Start

### 1. Install Dependencies

```bash
# Install Python dependencies
poetry install

# Or with pip
pip install -r requirements.txt
```

### 2. Start Database

```bash
# Start PostgreSQL with TimescaleDB
docker-compose up -d db

# Wait for database to be ready
docker-compose logs -f db
```

### 3. Initialize Database

```bash
# Run the initialization script
python -m db.init_db

# Or run migrations manually
alembic upgrade head
```

### 4. Seed Sample Data

```bash
# Populate with sample data
python -m db.seeds
```

## Database Schema

### Forums Table
```sql
CREATE TABLE forums (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    url VARCHAR(500) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);
```

### Posts Table
```sql
CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    forum_id INTEGER REFERENCES forums(id),
    ticker VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    author VARCHAR(255) NOT NULL,
    raw_text TEXT NOT NULL,
    clean_text TEXT NOT NULL,
    sentiment_score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Sentiment Aggregation Table (TimescaleDB Hypertable)
```sql
CREATE TABLE sentiment_agg (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    interval_start TIMESTAMP WITH TIME ZONE NOT NULL,
    interval_end TIMESTAMP WITH TIME ZONE NOT NULL,
    avg_score FLOAT NOT NULL,
    post_cnt INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Convert to hypertable
SELECT create_hypertable('sentiment_agg', 'interval_start', 
                        chunk_time_interval => INTERVAL '1 day');
```

### Alerts Table
```sql
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    rule VARCHAR(500) NOT NULL,
    triggered_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Usage Examples

### Basic Database Operations

```python
from db import SessionLocal
from db.models import Forum, Post

# Get database session
db = SessionLocal()

# Create a forum
forum = Forum(name="Test Forum", url="https://test.com")
db.add(forum)
db.commit()

# Query posts by ticker
posts = db.query(Post).filter(Post.ticker == "AAPL").all()

# Get sentiment aggregation
from db.models import SentimentAgg
sentiment = db.query(SentimentAgg).filter(
    SentimentAgg.ticker == "AAPL"
).order_by(SentimentAgg.interval_start.desc()).first()

db.close()
```

### Using the Session Dependency

```python
from db import get_db

def some_function():
    db = next(get_db())
    try:
        # Your database operations here
        pass
    finally:
        db.close()
```

## Migration Management

### Create a New Migration

```bash
# Generate migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1
```

### Migration History

```bash
# View migration history
alembic history

# View current migration
alembic current
```

## Testing

Run the database tests:

```bash
# Run all tests
pytest tests/test_db_models.py

# Run with coverage
pytest tests/test_db_models.py --cov=db
```

## Configuration

Database configuration is handled through environment variables:

- `DATABASE_URL` - PostgreSQL connection string
- `POSTGRES_HOST` - Database host (default: localhost)
- `POSTGRES_PORT` - Database port (default: 5432)
- `POSTGRES_DB` - Database name (default: nssm_db)
- `POSTGRES_USER` - Database user (default: nssm_user)
- `POSTGRES_PASSWORD` - Database password (default: nssm_password)

## TimescaleDB Features

The system leverages TimescaleDB for time-series data optimization:

- **Hypertables** for automatic partitioning of sentiment data
- **Time-based queries** for efficient historical analysis
- **Compression** for long-term data storage (configurable)
- **Continuous aggregates** for real-time analytics (future enhancement)

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure PostgreSQL container is running
2. **Migration Errors**: Check Alembic configuration and database URL
3. **TimescaleDB Extension**: Verify TimescaleDB image is being used
4. **Permission Errors**: Check database user permissions

### Debug Mode

Enable SQLAlchemy logging by setting `echo=True` in the engine creation:

```python
engine = create_engine(DATABASE_URL, echo=True)
```

## Development

### Adding New Models

1. Define the model in `db/models.py`
2. Create a new Alembic migration
3. Update tests in `tests/test_db_models.py`
4. Add sample data to `db/seeds.py`

### Database Design Principles

- Use appropriate data types and constraints
- Index frequently queried columns
- Implement proper foreign key relationships
- Consider TimescaleDB for time-series data
- Use transactions for data consistency

## Contributing

When making database changes:

1. Update models with proper documentation
2. Create corresponding migrations
3. Add comprehensive tests
4. Update this documentation
5. Test with sample data
