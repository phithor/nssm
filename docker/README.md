# NSSM Docker Services

This directory contains the Docker configuration for running the NSSM (Nordic Stock Sentiment Monitor) system as containerized services.

## Architecture Overview

The NSSM system consists of the following services:

- **db**: PostgreSQL with TimescaleDB for time-series data
- **dashboard**: Streamlit web application (external access on port 8501)
- **scraper**: Forum data collection service
- **nlp**: Natural language processing service
- **analytics**: Sentiment analysis and anomaly detection
- **market**: Market data collection service

## Network Architecture

- **nssm-internal**: Internal network for service-to-service communication
- **nssm-external**: External network for services needing external access (dashboard)

## Quick Start

### Prerequisites

1. Docker and Docker Compose installed
2. Copy `env.example` to `.env` and configure your settings:
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

### Starting All Services

```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

### Starting Individual Services

```bash
# Start only the database
docker-compose up db

# Start dashboard only
docker-compose up dashboard

# Start all background services
docker-compose up scraper nlp analytics market
```

## Service Configuration

### Environment Variables

All services use the following environment variables (defined in `.env`):

- `DATABASE_URL`: PostgreSQL connection string
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`: Database connection details
- `SCRAPER_INTERVAL_MINUTES`: Scraper execution interval (default: 60)
- `MARKET_INTERVAL_MINUTES`: Market data collection interval (default: 30)
- `ANALYTICS_HOURS_BACK`: Analytics lookback period (default: 24)
- `LOG_LEVEL`: Logging level (default: INFO)

### Service-Specific Commands

#### Manual Execution

```bash
# Run scraper manually (one-time execution)
docker-compose run --rm scraper /app/scripts/entrypoint-scraper.sh manual

# Run analytics manually
docker-compose run --rm analytics /app/scripts/entrypoint-analytics.sh manual

# Run market data collection manually
docker-compose run --rm market /app/scripts/entrypoint-market.sh manual
```

#### Cron Scheduling

Services automatically run on schedules when started with their default commands:

- **Analytics**: Runs hourly at :00
- **Scraper**: Runs every 60 minutes (configurable)
- **Market**: Runs every 30 minutes (configurable)
- **NLP**: Runs on-demand (no cron scheduling)

## Development Workflow

### Building Base Images

```bash
# Build the base image (contains common dependencies)
docker build -f Dockerfile.base -t nssm-base:latest .

# Build all service images
docker-compose build
```

### Debugging Services

```bash
# View service logs
docker-compose logs [service-name]

# Follow logs in real-time
docker-compose logs -f [service-name]

# Execute commands in running containers
docker-compose exec [service-name] bash

# Check service health
docker-compose ps
```

### Scaling Services

```bash
# Scale scraper service to 2 instances
docker-compose up -d --scale scraper=2

# Scale analytics service
docker-compose up -d --scale analytics=3
```

## Health Checks

All services include health checks:

- **Database**: PostgreSQL connectivity check
- **Dashboard**: HTTP health endpoint check
- **Worker Services**: Python module import check

Health status can be monitored with:
```bash
docker-compose ps
```

## Volumes and Persistence

The following volumes are created for data persistence:

- `postgres_data`: Database data
- `scraper_logs`: Scraper service logs
- `nlp_logs`: NLP service logs
- `analytics_logs`: Analytics service logs
- `analytics_data`: Analytics output data
- `market_logs`: Market service logs
- `market_cache`: Market data cache

## Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure port 8501 is available for the dashboard
2. **Database connection**: Verify PostgreSQL credentials in `.env`
3. **Permission issues**: Ensure scripts have execute permissions
4. **Memory issues**: Increase Docker memory allocation for large datasets

### Service Dependencies

Services start in the correct order due to `depends_on` configuration:
1. Database (must be healthy)
2. Worker services (scraper, nlp, analytics, market)
3. Dashboard (last, as it depends on data being available)

### Logs and Monitoring

```bash
# View all logs
docker-compose logs

# View specific service logs with timestamps
docker-compose logs -f -t [service-name]

# Export logs for analysis
docker-compose logs [service-name] > service.log
```

## Production Deployment

For production deployment:

1. Use environment-specific `.env` files
2. Configure proper logging and monitoring
3. Set up backup strategies for volumes
4. Configure resource limits in docker-compose.yml
5. Use reverse proxy (nginx) for the dashboard
6. Set up proper secrets management

## Service Entrypoints

Each service has an entrypoint script in `scripts/`:

- `entrypoint-analytics.sh`: Analytics scheduler
- `entrypoint-scraper.sh`: Forum scraper
- `entrypoint-nlp.sh`: NLP processor
- `entrypoint-market.sh`: Market data collector

These scripts handle:
- Environment variable loading
- Cron job setup
- Logging directory creation
- Service initialization

## API Endpoints

- **Dashboard**: http://localhost:8501
- **Database**: localhost:5432 (internal only)

## Security Considerations

- Database is only accessible internally
- Dashboard is the only externally exposed service
- All services run with non-root users
- Secrets are managed via environment variables
