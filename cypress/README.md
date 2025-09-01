# NSSM Dashboard Cypress E2E Tests

This directory contains end-to-end tests for the NSSM Streamlit dashboard using Cypress.

## Test Coverage

The Cypress tests verify:

- ✅ Dashboard loads successfully
- ✅ Main UI elements are present (header, sidebar, metrics)
- ✅ Sidebar filters work correctly
- ✅ Responsive design across different viewports
- ✅ Performance (page load times under 10 seconds)
- ✅ Container exposes port 8501 correctly

## Running Tests Locally

### Prerequisites

1. Install dependencies:
   ```bash
   poetry install --with dev
   npm install cypress@^13.6.0
   ```

2. Start the dashboard:
   ```bash
   poetry run streamlit run dashboard/app.py --server.port=8501
   ```

3. Run Cypress tests:
   ```bash
   npx cypress run --config baseUrl=http://localhost:8501
   ```

### Using the Test Runner Script

Alternatively, use the provided script which handles container management:

```bash
./scripts/run_cypress_tests.sh
```

This script will:
- Build and start the dashboard container
- Wait for the dashboard to be ready
- Run Cypress tests
- Clean up containers

## CI/CD Integration

Tests are automatically run in GitHub Actions on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches
- Changes to dashboard, Cypress, or test runner files

### Workflow Features

- Container-based testing for consistency
- Automatic screenshots and videos on failure
- Full container lifecycle management
- Performance monitoring

## Test Structure

```
cypress/
├── e2e/
│   └── dashboard.cy.js    # Main dashboard test suite
├── README.md             # This file
└── config.js            # Cypress configuration
```

## Container Verification

The tests verify that:

1. **Port Exposure**: Container exposes port 8501
2. **Service Health**: Dashboard responds to HTTP requests
3. **Content Loading**: Main dashboard elements load within acceptable time
4. **UI Functionality**: Basic interactions work correctly

## Troubleshooting

### Dashboard Not Starting
- Check container logs: `docker-compose logs dashboard`
- Verify port 8501 is not in use
- Ensure database is running and accessible

### Tests Failing
- Check Cypress version compatibility
- Verify baseUrl configuration
- Check for network timeouts

### Performance Issues
- Increase timeout values in `cypress.config.js`
- Check container resource allocation
- Monitor network latency

## Configuration

Test configuration can be modified in `cypress.config.js`:

```javascript
{
  baseUrl: 'http://localhost:8501',
  viewportWidth: 1280,
  viewportHeight: 720,
  defaultCommandTimeout: 10000,
  // ... other options
}
```
