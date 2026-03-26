"""
Climate Data Extraction - Google-First Discovery Engine
Primary: Google Custom Search API (most reliable)
Secondary: Playwright for JavaScript-heavy sites
"""

import os
import re
import time
import asyncio
import hashlib
import requests
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse, quote_plus

# Use simple logging - don't depend on complex config
import logging
logger = logging.getLogger(__name__)


@dataclass
class DiscoveredReport:
    """Represents a discovered PDF report"""
    url: str
    title: str
    company: str
    year: Optional[int] = None
    source: str = "google"  # google, playwright, duckduckgo
    file_size: Optional[int] = None
    local_path: Optional[str] = None

    def __repr__(self):
        return f"Report({self.company}, {self.year}, {self.source})"


class GoogleDiscovery:
    """
    Google Custom Search API - Most reliable PDF discovery method
    FREE: 100 queries/day
    """

    def __init__(self):
        self.api_key = os.getenv('GOOGLE_API_KEY', '')
        self.cse_id = os.getenv('GOOGLE_CSE_ID', '')
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    def is_configured(self) -> bool:
        """Check if Google API is configured"""
        return bool(self.api_key and self.cse_id)

    def search_pdfs(self, company_name: str, max_results: int = 10) -> List[DiscoveredReport]:
        """
        Search Google for company sustainability PDFs

        Args:
            company_name: Company to search for
            max_results: Maximum PDFs to find

        Returns:
            List of discovered reports
        """
        if not self.is_configured():
            logger.warning("Google API not configured - set GOOGLE_API_KEY and GOOGLE_CSE_ID")
            return []

        reports = []
        queries = [
            f'{company_name} sustainability report filetype:pdf',
            f'{company_name} ESG report filetype:pdf',
            f'{company_name} climate report filetype:pdf',
            f'{company_name} annual environmental report filetype:pdf',
        ]

        seen_urls = set()

        for query in queries:
            if len(reports) >= max_results:
                break

            try:
                results = self._search(query)

                for item in results:
                    url = item.get('link', '')

                    # Skip duplicates
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    # Only PDFs
                    if not url.lower().endswith('.pdf'):
                        continue

                    title = item.get('title', '')
                    year = self._extract_year(title + ' ' + url)

                    reports.append(DiscoveredReport(
                        url=url,
                        title=title,
                        company=company_name,
                        year=year,
                        source='google'
                    ))

                    if len(reports) >= max_results:
                        break

                # Rate limit
                time.sleep(1)

            except Exception as e:
                logger.error(f"Google search failed for '{query}': {e}")

        logger.info(f"Google found {len(reports)} PDFs for {company_name}")
        return reports

    def _search(self, query: str, num: int = 10) -> List[Dict]:
        """Execute Google Custom Search API call"""
        params = {
            'key': self.api_key,
            'cx': self.cse_id,
            'q': query,
            'num': min(num, 10),  # Max 10 per request
        }

        response = requests.get(self.base_url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        return data.get('items', [])

    def _extract_year(self, text: str) -> Optional[int]:
        """Extract year from text"""
        match = re.search(r'\b(20(?:1[5-9]|2[0-9]))\b', text)
        return int(match.group(1)) if match else None


class DuckDuckGoDiscovery:
    """
    DuckDuckGo HTML scraping - Free fallback (no API key needed)
    """

    def __init__(self):
        self.base_url = "https://html.duckduckgo.com/html/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
        })

    def search_pdfs(self, company_name: str, max_results: int = 10) -> List[DiscoveredReport]:
        """Search DuckDuckGo for PDFs"""
        from bs4 import BeautifulSoup

        reports = []
        query = f'{company_name} sustainability report filetype:pdf'

        try:
            response = self.session.post(
                self.base_url,
                data={'q': query},
                timeout=30
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            for result in soup.select('.result__a'):
                url = result.get('href', '')

                # Extract actual URL from DDG redirect
                if 'uddg=' in url:
                    from urllib.parse import parse_qs, urlparse as parse_url
                    parsed = parse_url(url)
                    params = parse_qs(parsed.query)
                    if 'uddg' in params:
                        url = params['uddg'][0]

                if url.lower().endswith('.pdf'):
                    title = result.get_text(strip=True)
                    year = self._extract_year(title + ' ' + url)

                    reports.append(DiscoveredReport(
                        url=url,
                        title=title,
                        company=company_name,
                        year=year,
                        source='duckduckgo'
                    ))

                    if len(reports) >= max_results:
                        break

        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")

        logger.info(f"DuckDuckGo found {len(reports)} PDFs for {company_name}")
        return reports

    def _extract_year(self, text: str) -> Optional[int]:
        match = re.search(r'\b(20(?:1[5-9]|2[0-9]))\b', text)
        return int(match.group(1)) if match else None


class PlaywrightDiscovery:
    """
    Playwright-based discovery for JavaScript-heavy websites
    Slower but handles SPAs like Tesla.com
    """

    def __init__(self, download_dir: str = "./data/reports"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    async def scrape_website(self, company_name: str, website_url: str) -> List[DiscoveredReport]:
        """Scrape company website for PDF links using Playwright"""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("Playwright not installed - run: pip install playwright && playwright install chromium")
            return []

        reports = []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
                )
                page = await context.new_page()

                # Navigate to website
                await page.goto(website_url, wait_until='networkidle', timeout=30000)

                # Find sustainability-related links
                links = await page.eval_on_selector_all('a[href]', '''elements =>
                    elements.map(el => ({
                        href: el.href,
                        text: (el.innerText || '').trim().toLowerCase()
                    }))
                ''')

                keywords = ['sustainability', 'esg', 'environmental', 'climate', 'carbon', 'impact']

                # Find PDF links
                for link in links:
                    href = link.get('href', '')
                    text = link.get('text', '')

                    is_pdf = href.lower().endswith('.pdf')
                    is_relevant = any(kw in text for kw in keywords) or any(kw in href.lower() for kw in keywords)

                    if is_pdf or is_relevant:
                        year = self._extract_year(href + ' ' + text)

                        reports.append(DiscoveredReport(
                            url=href,
                            title=text or href.split('/')[-1],
                            company=company_name,
                            year=year,
                            source='playwright'
                        ))

                await browser.close()

        except Exception as e:
            logger.error(f"Playwright scraping failed for {website_url}: {e}")

        logger.info(f"Playwright found {len(reports)} links for {company_name}")
        return reports

    def scrape_website_sync(self, company_name: str, website_url: str) -> List[DiscoveredReport]:
        """Synchronous wrapper for Playwright scraping"""
        return asyncio.run(self.scrape_website(company_name, website_url))

    def _extract_year(self, text: str) -> Optional[int]:
        match = re.search(r'\b(20(?:1[5-9]|2[0-9]))\b', text)
        return int(match.group(1)) if match else None


class UnifiedDiscovery:
    """
    Unified discovery engine - combines all sources
    Priority: Google API > DuckDuckGo > Playwright
    """

    def __init__(self, download_dir: str = "./data/reports"):
        self.google = GoogleDiscovery()
        self.duckduckgo = DuckDuckGoDiscovery()
        self.playwright = PlaywrightDiscovery(download_dir)
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def discover_reports(self,
                        company_name: str,
                        website: Optional[str] = None,
                        max_reports: int = 10,
                        use_playwright: bool = False) -> List[DiscoveredReport]:
        """
        Discover PDF reports for a company using multiple sources

        Args:
            company_name: Company name
            website: Optional company website for Playwright scraping
            max_reports: Maximum reports to find
            use_playwright: Whether to use Playwright (slower but handles JS)

        Returns:
            List of discovered reports, deduplicated
        """
        all_reports = []
        seen_urls = set()

        # 1. Try Google API first (most reliable)
        if self.google.is_configured():
            logger.info(f"Searching Google for {company_name}...")
            google_reports = self.google.search_pdfs(company_name, max_reports)
            for r in google_reports:
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    all_reports.append(r)

        # 2. Try DuckDuckGo as fallback
        if len(all_reports) < max_reports:
            logger.info(f"Searching DuckDuckGo for {company_name}...")
            ddg_reports = self.duckduckgo.search_pdfs(company_name, max_reports - len(all_reports))
            for r in ddg_reports:
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    all_reports.append(r)

        # 3. Use Playwright for website scraping (optional, slower)
        if use_playwright and website and len(all_reports) < max_reports:
            logger.info(f"Scraping {website} with Playwright...")
            pw_reports = self.playwright.scrape_website_sync(company_name, website)
            for r in pw_reports:
                if r.url not in seen_urls and r.url.lower().endswith('.pdf'):
                    seen_urls.add(r.url)
                    all_reports.append(r)

        logger.info(f"Total discovered: {len(all_reports)} reports for {company_name}")
        return all_reports[:max_reports]

    def download_report(self, report: DiscoveredReport, company_name: str) -> Optional[Path]:
        """Download a PDF report"""
        try:
            # Create company directory
            company_dir = self.download_dir / company_name.lower().replace(' ', '_')
            company_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename
            url_hash = hashlib.md5(report.url.encode()).hexdigest()[:8]
            year_str = str(report.year) if report.year else 'unknown'
            filename = f"{company_name.lower().replace(' ', '_')}_{year_str}_{url_hash}.pdf"
            filepath = company_dir / filename

            # Skip if already downloaded
            if filepath.exists():
                logger.info(f"Already downloaded: {filepath}")
                report.local_path = str(filepath)
                return filepath

            # Download
            logger.info(f"Downloading: {report.url[:80]}...")
            response = requests.get(
                report.url,
                timeout=60,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'},
                stream=True
            )
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' not in content_type.lower() and not report.url.lower().endswith('.pdf'):
                logger.warning(f"Not a PDF: {content_type}")
                return None

            # Save file
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = filepath.stat().st_size
            logger.info(f"Downloaded: {filepath} ({file_size / 1024 / 1024:.1f} MB)")

            report.local_path = str(filepath)
            report.file_size = file_size

            return filepath

        except Exception as e:
            logger.error(f"Download failed for {report.url}: {e}")
            return None
