# NSSM MariaDB Setup Guide

This guide explains how to configure NSSM to work with MariaDB instead of TimescaleDB/PostgreSQL.

## Prerequisites

- MariaDB/MySQL server running (version 10.3+ recommended)
- Database user with appropriate permissions
- NSSM project with updated dependencies

## Quick Setup

### 1. Install MySQL Dependencies

```bash
# If not already done
poetry install
```

### 2. Configure Environment Variables

Copy the MariaDB configuration:

```bash
cp mariadb-config.env .env
```

Edit `.env` and update the database connection details:

```bash
# For Docker container named 'mariadb'
DATABASE_URL=mysql+pymysql://nssm_user:your_password@mariadb:3306/nssm_db

# For host-based MariaDB
DATABASE_URL=mysql+pymysql://nssm_user:your_password@localhost:3306/nssm_db

# For remote MariaDB server
DATABASE_URL=mysql+pymysql://nssm_user:your_password@your-server.com:3306/nssm_db
```

### 3. Database Setup

Create the database and user (run these in your MariaDB):

```sql
-- Create database
CREATE DATABASE nssm_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user
CREATE USER 'nssm_user'@'%' IDENTIFIED BY 'your_secure_password';

-- Grant permissions
GRANT ALL PRIVILEGES ON nssm_db.* TO 'nssm_user'@'%';

-- Flush privileges
FLUSH PRIVILEGES;
```

### 4. Deploy with Docker Compose

Use the MariaDB-specific compose file:

```bash
# Deploy all services
docker-compose -f docker-compose.mariadb.yml up --build

# Or run in background
docker-compose -f docker-compose.mariadb.yml up -d --build
```

## Database Schema Migration

After setting up the database connection, create the schema:

```bash
# Generate initial migration
alembic revision --autogenerate -m "Initial schema for MariaDB"

# Apply migration
alembic upgrade head
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | - | Full database connection URL |
| `MYSQL_HOST` | mariadb | Database host |
| `MYSQL_PORT` | 3306 | Database port |
| `MYSQL_DB` | nssm_db | Database name |
| `MYSQL_USER` | nssm_user | Database username |
| `MYSQL_PASSWORD` | - | Database password |

### Connection URL Formats

```bash
# MariaDB container (recommended)
mysql+pymysql://user:pass@mariadb:3306/database

# Local MariaDB
mysql+pymysql://user:pass@localhost:3306/database

# Remote MariaDB
mysql+pymysql://user:pass@server.com:3306/database
```

## Troubleshooting

### Connection Issues

1. **Access denied**: Check username/password and permissions
2. **Can't connect to MySQL server**: Verify host and port
3. **Unknown database**: Create the database first
4. **Character encoding**: Use utf8mb4 for full Unicode support

### Migration Issues

If you encounter migration issues:

```bash
# Reset migrations
alembic downgrade base
alembic upgrade head

# Or recreate from scratch
drop database nssm_db;
create database nssm_db character set utf8mb4 collate utf8mb4_unicode_ci;
alembic upgrade head
```

### Performance Tuning

For MariaDB, consider these settings in your `my.cnf`:

```ini
[mysqld]
innodb_buffer_pool_size=1G
innodb_log_file_size=256M
max_connections=200
character-set-server=utf8mb4
collation-server=utf8mb4_unicode_ci
```

## Differences from PostgreSQL

### Removed Features
- **Table partitioning**: Not supported in MariaDB's free version
- **Advanced time-series functions**: Use MariaDB's built-in functions instead

### Retained Features
- **All core functionality**: Scraping, NLP, analytics work identically
- **ACID compliance**: Full transaction support
- **Index support**: All performance optimizations work
- **Foreign keys**: Relationship constraints maintained

## Migration from PostgreSQL

If migrating from an existing PostgreSQL setup:

1. Export data from PostgreSQL
2. Create MariaDB database
3. Import data (may need format conversion)
4. Update connection strings
5. Test all functionality

The SQLAlchemy ORM handles most compatibility issues automatically.

## Support

For MariaDB-specific issues, consult:
- [MariaDB Documentation](https://mariadb.com/kb/en/)
- [SQLAlchemy MySQL Dialect](https://docs.sqlalchemy.org/en/20/dialects/mysql.html)
- [PyMySQL Documentation](https://pymysql.readthedocs.io/)
