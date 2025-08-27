# Nordic Stock Sentiment Monitor (NSSM)

A personal research assistant that provides real-time monitoring of Nordic investor forums and correlates them with market data and official news to identify alpha-moving opportunities.

## 🎯 Problem Statement

Scandinavian retail forums like Hegnar Online and Avanza Forum generate alpha-moving chatter, but following them manually is inefficient and nearly impossible at scale. NSSM automates collection → sentiment analysis → alerting so you can spot unusual "buzz" and emerging momentum in specific stocks before markets or media react.

## 🏗️ Architecture Overview

NSSM is built as a modular system with the following core components:

```
NSSM/
├── scraper/          # Forum scraping & data collection
├── db/              # Database models & migrations
├── nlp/             # Sentiment analysis & NLP pipeline
├── dashboard/       # Streamlit web interface
├── config/          # Configuration management
└── tests/           # Test suite
```

### Core System Components

1. **Forum Scrapers** (`scraper/`)
   - Custom-built scrapers for Hegnar Online and Avanza Forum
   - Heuristic-based parsing with cron scheduling
   - Raw data ingestion into local database

2. **Sentiment & Momentum Analyzer** (`nlp/`)
   - ML models fine-tuned on Scandinavian text
   - Aggregated sentiment per stock per time interval
   - Anomaly detection using rolling averages & volatility thresholds

3. **Data Storage** (`db/`)
   - PostgreSQL with TimescaleDB extension for time-series queries
   - Structured storage for posts, stocks, and alerts
   - Raw log storage for debugging and analysis

4. **Personal Dashboard** (`dashboard/`)
   - Streamlit-based web interface
   - Dynamic plots showing buzz levels and sentiment trends
   - Interactive stock exploration and timeline views

5. **Alerting Engine** (`nlp/`)
   - Local notifications and terminal logs
   - Configurable alert conditions
   - Optional webhook integration for mobile notifications

6. **Market Data Integration** (`scraper/`)
   - OpenBB SDK integration for financial data
   - RSS feeds from Oslo Børs and Nasdaq OMX
   - News correlation with forum sentiment

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Docker & Docker Compose

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd NSSM
   ```

2. **Set up the environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Configure the database**
   ```bash
   # Start PostgreSQL with Docker
   docker-compose up -d postgres
   
   # Run database migrations
   python -m db.migrate
   ```

4. **Launch the dashboard**
   ```bash
   streamlit run dashboard/main.py
   ```

## 📊 Data Flow

```
Forum Scrapers → Raw Data Storage → NLP Pipeline → Sentiment Analysis → Database → Dashboard
     ↓                    ↓              ↓              ↓              ↓         ↓
  Hegnar/Avanza    PostgreSQL Raw   Scandinavian   Aggregated     Time-series  Real-time
     Forums           Logs         ML Models      Sentiment      Queries      Visualization
```

## 🔧 Configuration

The system uses environment variables for configuration:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/nssm

# API Keys
OPENBB_API_KEY=your_key_here
YAHOO_FINANCE_API_KEY=your_key_here

# Scraping Settings
SCRAPER_DELAY=5  # seconds between requests
SCRAPER_USER_AGENT=Mozilla/5.0...
```

## 🧪 Development

### Running Tests
```bash
pytest -v
```

### Code Quality
```bash
# Format code
black .
isort .

# Lint code
flake8 .
```

### Pre-commit Hooks
The project includes pre-commit hooks for:
- Code formatting (black, isort)
- Linting (flake8)
- Type checking (mypy)

## 📈 Roadmap

### MVP (Current Focus)
- [x] Project initialization and structure
- [ ] Basic forum scraping (Hegnar + Avanza)
- [ ] Simple sentiment classification
- [ ] PostgreSQL database setup
- [ ] Basic dashboard with top buzzing stocks

### Next Iteration
- [ ] Anomaly detection for buzz spikes
- [ ] Basic alerting system
- [ ] OpenBB market data integration
- [ ] Enhanced NLP pipeline

### Future Enhancements
- [ ] Additional forums and social media sources
- [ ] Advanced anomaly detection (rolling z-scores)
- [ ] Personal forecasting module
- [ ] Multi-user SaaS capabilities

## 🚨 Risk Mitigation

- **Forum Blocking**: Rotate IPs, user-agents, and implement polite scraping delays
- **NLP Accuracy**: Custom keyword lexicon for Scandinavian finance slang
- **Data Overload**: Focus on ticker mentions, avoid storing irrelevant posts
- **Infrastructure Complexity**: Keep MVP simple, optimize later

## 📝 License

This project is for personal research use. Commercial use requires proper licensing and compliance with forum terms of service.

## 🤝 Contributing

This is currently a personal research tool. Future contributions will be welcome once the project matures.

---

**Built with ❤️ for Nordic market research**
