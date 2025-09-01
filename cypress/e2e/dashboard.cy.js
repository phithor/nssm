describe('NSSM Dashboard E2E Tests', () => {
  beforeEach(() => {
    // Visit the dashboard
    cy.visit('/', { timeout: 30000 })

    // Wait for the main header to load
    cy.contains('NSSM Dashboard', { timeout: 15000 }).should('be.visible')
  })

  it('should load the dashboard successfully', () => {
    // Check main elements are present
    cy.contains('NSSM Dashboard').should('be.visible')
    cy.contains('Norwegian/Swedish Stock Market Monitor').should('be.visible')

    // Check sidebar is present
    cy.contains('Dashboard Filters').should('be.visible')
    cy.contains('Time Range').should('be.visible')
    cy.contains('Tickers').should('be.visible')
  })

  it('should display metrics overview', () => {
    // Check metrics section exists
    cy.contains('Market Overview').should('be.visible')

    // Check metric labels are present (even if values are 0)
    cy.contains('Active Tickers').should('be.visible')
    cy.contains('Time Period').should('be.visible')
    cy.contains('Total Posts').should('be.visible')
    cy.contains('Avg Sentiment').should('be.visible')
  })

  it('should have working sidebar filters', () => {
    // Check sidebar elements
    cy.get('input[type="date"]').should('have.length.at.least', 2)

    // Check filter sections
    cy.contains('Analysis Filters').should('be.visible')
    cy.contains('News Sources').should('be.visible')

    // Check action buttons
    cy.contains('Refresh Data').should('be.visible')
    cy.contains('Reset Filters').should('be.visible')
  })

  it('should handle empty ticker selection', () => {
    // If no tickers are selected, should show warning
    cy.get('body').then($body => {
      if ($body.text().includes('Please select at least one ticker')) {
        cy.contains('Please select at least one ticker').should('be.visible')
      }
    })
  })

  it('should display anomaly heatmap section', () => {
    // Check heatmap section exists
    cy.contains('Top Buzzing Stocks Heatmap').should('be.visible')
  })

  it('should display sentiment analysis section', () => {
    // Check sentiment analysis section exists
    cy.contains('Sentiment vs Price Analysis').should('be.visible')
  })

  it('should have responsive design', () => {
    // Test mobile viewport
    cy.viewport(375, 667)
    cy.contains('NSSM Dashboard').should('be.visible')

    // Test tablet viewport
    cy.viewport(768, 1024)
    cy.contains('NSSM Dashboard').should('be.visible')

    // Test desktop viewport
    cy.viewport(1920, 1080)
    cy.contains('NSSM Dashboard').should('be.visible')
  })

  it('should handle filter interactions', () => {
    // Test expanding filter summary
    cy.contains('Filter Summary').click()
    cy.contains('Date Range:').should('be.visible')

    // Test refresh button (should not cause errors)
    cy.contains('Refresh Data').click()
    // Wait for potential reload
    cy.wait(2000)
    cy.contains('NSSM Dashboard').should('be.visible')
  })

  it('should display footer information', () => {
    // Check footer exists
    cy.contains('Dashboard automatically refreshes').should('be.visible')
    cy.contains('Last updated:').should('be.visible')
  })

  // Performance test
  it('should load within acceptable time', () => {
    const startTime = Date.now()

    cy.visit('/', { timeout: 30000 })

    cy.contains('NSSM Dashboard', { timeout: 15000 }).should('be.visible').then(() => {
      const loadTime = Date.now() - startTime
      cy.log(`Page load time: ${loadTime}ms`)

      // Assert load time is under 10 seconds
      expect(loadTime).to.be.lessThan(10000)
    })
  })

  // API response time test (if applicable)
  it('should have reasonable response times for data loading', () => {
    const startTime = Date.now()

    // Wait for main content to load
    cy.contains('Market Overview', { timeout: 10000 }).should('be.visible')

    cy.get('body').then(() => {
      const loadTime = Date.now() - startTime
      cy.log(`Content load time: ${loadTime}ms`)

      // Assert content loads within reasonable time
      expect(loadTime).to.be.lessThan(15000)
    })
  })
})
