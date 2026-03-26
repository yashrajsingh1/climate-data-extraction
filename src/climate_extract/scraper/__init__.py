"""
Climate Data Extraction System - Playwright Scraper Module

JavaScript-capable web scraper for modern websites with bot protection bypass.
"""

from .playwright_scraper import (
    PlaywrightScraper,
    PlaywrightScraperManager,
    ScrapedReport,
    scrape_company_reports,
    scrape_company_sync,
)

__all__ = [
    'PlaywrightScraper',
    'PlaywrightScraperManager',
    'ScrapedReport',
    'scrape_company_reports',
    'scrape_company_sync',
]
