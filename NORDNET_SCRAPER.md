# Nordnet Shareville Scraper

This document describes the implementation of the Nordnet Shareville forum scraper for the NSSM project.

## Overview

The Nordnet Shareville scraper extracts posts from Nordnet's social investment platform for specific stock tickers. It's designed to capture investor sentiment and discussions about Scandinavian stocks from:

- **Main Forum**: https://www.nordnet.no/aksjeforum
- **Ticker-Specific Pages**: https://www.nordnet.no/aksjer/kurser/{company-name}-{ticker}-{exchange}
- **Examples**:
  - ENSU: https://www.nordnet.no/aksjer/kurser/ensurge-micropower-ensu-xosl
  - NOVO: https://www.nordnet.no/aksjer/kurser/novo-nordisk-b-novo-b-xcse

## Features

- **Multi-ticker scraping**: Scrapes posts for all stocks or specific tickers
- **Automatic fallback**: Uses Selenium when JavaScript rendering is required
- **Norwegian language support**: Handles Norwegian date formats and text
- **Likes extraction**: Captures post engagement metrics
- **Robust parsing**: Multiple fallback selectors for different HTML structures
- **Nested comments support**: Handles threaded discussions and replies

## Implementation Details

### File Structure

```
scraper/
├── nordnet.py              # Main Nordnet scraper implementation
├── persistence.py           # Updated to include Nordnet scraper
└── __main__.py             # CLI entry point (already supports all scrapers)

db/
├── seeds.py                 # Updated to include Nordnet Shareville forum
└── models.py               # Existing Post model (no changes needed)

test_nordnet_scraper.py     # Test script for Nordnet scraper
test_complete_scraping.py   # Test script for complete pipeline
```

### Key Components

#### NordnetScraper Class

The main scraper class that inherits from the base `Scraper` class:

```python
class NordnetScraper(Scraper):
    def __init__(self, use_selenium_fallback: bool = True):
        # Initialize with Nordnet-specific configuration
        super().__init__(base_url="https://www.nordnet.no")
        
    def scrape_ticker_posts(self, ticker: str, max_pages: int = 5) -> List[Post]:
        # Scrape posts for a specific ticker
```

#### HTML Selectors

The scraper uses precise selectors based on the actual Nordnet HTML structure:

```python
self.selectors = {
    "post_container": "li.ListItem__StyledListItem-sc-pn91gs-0",
    "author_container": "div.Flexbox__StyledFlexbox-sc-1ob4g1e-0.hqaqcx > a.Link__StyledLink-sc-apj04t-0",
    "author_name": "div.Flexbox__StyledFlexbox-sc-1ob4g1e-0.haAnAc > span > a.Link__StyledLink-sc-apj04t-0",
    "content": "div.Content-styled__MarkContentFlexbox-sc-d426b66b-3 > div.CssGrid__StyledDiv-sc-bu5cxy-0",
    "timestamp": "div.Flexbox__StyledFlexbox-sc-1ob4g1e-0.hllVYC > span.Typography__Span-sc-10mju41-0",
    "likes": "button.NormalizedButton__Button-sc-ey7f5x-0.Button__StyledButton-sc-rtfjm6-0.glaBYD",
    "likes_count": "span.lmVbIM, .likes-count",
    "nested_posts": "li.ListItem__StyledListItem-sc-pn91gs-0 li.ListItem__StyledListItem-sc-pn91gs-0",
}
```

#### Norwegian Date Parsing

Handles Norwegian date formats:

```python
def _parse_timestamp(self, timestamp_text: str) -> datetime:
    # Examples: "for 1 døgn siden", "2 timer siden", "15. aug.", "2024-08-15"
    
    # Norwegian month abbreviations
    month_map = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "mai": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "des": 12
    }
```

## Usage

### Command Line

Run the scraper as part of the complete pipeline:

```bash
# Run all scrapers including Nordnet
python -m scraper run --once --max-pages 5

# Run continuously
python -m scraper run --interval 5 --max-pages 3
```

### Programmatic Usage

```python
from scraper.persistence import ScraperPersistence

# Initialize persistence layer
with ScraperPersistence() as persistence:
    # Scrape Nordnet Shareville for all stocks
    result = persistence.scrape_and_store_nordnet(max_pages=5)
    print(f"Found {result['posts_found']} posts, stored {result['posts_stored']}")
    
    # Or scrape for a specific ticker
    result = persistence.scrape_and_store_nordnet("ENSU", max_pages=5)
    print(f"Found {result['posts_found']} posts for ENSU, stored {result['posts_stored']}")
```

### Testing

Test the Nordnet scraper specifically:

```bash
# Test Nordnet scraper
python test_nordnet_scraper.py

# Test complete pipeline
python test_complete_scraping.py
```

## Database Integration

### Forum Entry

The Nordnet Shareville forum is automatically added to the database:

```python
# In db/seeds.py
forums_data = [
    # ... other forums ...
    {"name": "Nordnet Shareville", "url": "https://www.nordnet.no/shareville"},
]
```

### Post Storage

Posts are stored with the following metadata:

```python
post = Post(
    forum_id=forum_id,
    post_id=f"nordnet_{hash(f'{author}_{timestamp}_{title}')}",
    ticker=ticker,  # Extracted from content or URL
    timestamp=timestamp,
    author=author,
    raw_text=raw_text,
    clean_text=raw_text,  # Will be cleaned by NLP pipeline
    url=post_url,
    scraper_metadata={
        "source": "nordnet_shareville",
        "parsed_at": datetime.now().isoformat(),
        "title": title,
        "likes_count": likes_count,
    }
)
```

## Configuration

### Environment Variables

The scraper uses the same environment variables as other scrapers:

- `DATABASE_URL`: Database connection string
- Any API keys for AI models (if using research features)

### Scraper Settings

Key configuration options:

- `use_selenium_fallback`: Enable/disable Selenium fallback (default: True)
- `max_pages`: Maximum pages to scrape per ticker (default: 5)
- `ticker_pattern`: Regex pattern for Norwegian stock tickers

## Error Handling

The scraper includes robust error handling:

1. **Robots.txt compliance**: Checks robots.txt before scraping
2. **Request failures**: Graceful handling of network errors
3. **JavaScript fallback**: Automatic fallback to Selenium when needed
4. **Parsing errors**: Continues processing even if individual posts fail to parse
5. **Database errors**: Transaction rollback on database errors

## Monitoring

### Logging

The scraper provides detailed logging:

```python
logger.info(f"Scraping page {page} for ticker {ticker}: {url}")
logger.info(f"Found {len(page_posts)} posts on page {page}")
logger.warning(f"Could not find Shareville section in HTML")
logger.error(f"Error scraping page {page} for {ticker}: {e}")
```

### Metrics

Track scraping performance:

- Posts found vs stored
- Success rate per forum
- Processing time per page
- Error rates

## Future Enhancements

Potential improvements:

1. **Multi-ticker support**: Scrape multiple tickers in parallel
2. **Advanced sentiment**: Pre-filter posts by sentiment keywords
3. **Rate limiting**: More sophisticated rate limiting
4. **Caching**: Cache scraped content to avoid re-scraping
5. **API integration**: Use Nordnet's API if available

## Troubleshooting

### Common Issues

1. **No posts found**: Check if the HTML structure has changed
2. **JavaScript errors**: Verify Selenium is properly configured
3. **Database errors**: Check database connection and schema
4. **Rate limiting**: Add delays between requests

### Debug Mode

Enable verbose logging:

```bash
python -m scraper run --verbose --once
```

### Manual Testing

Test individual components:

```python
from scraper.nordnet import NordnetScraper

scraper = NordnetScraper()

# Test main forum
html = scraper.fetch("https://www.nordnet.no/aksjeforum")
posts = scraper.parse(html)
print(f"Found {len(posts)} posts from main forum")

# Test specific ticker
html = scraper.fetch("https://www.nordnet.no/aksjer/kurser/ensurge-micropower-ensu-xosl")
posts = scraper.parse(html)
print(f"Found {len(posts)} posts for ENSU")

# Test ticker scraping method
posts = scraper.scrape_ticker_posts("ENSU", max_pages=1)
print(f"Found {len(posts)} posts for ENSU using scraping method")
```
