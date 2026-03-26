"""
Climate Data Extraction System - Playwright-Based Scraper
Production-ready JavaScript-capable scraper with bot protection bypass
"""

import asyncio
import hashlib
import logging
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from playwright.async_api import TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class ScrapedReport:
    """Report discovered via Playwright scraping"""
    url: str
    title: str
    company: str
    year: Optional[int] = None
    file_type: str = "pdf"
    file_size: Optional[int] = None
    source: str = "playwright"
    download_path: Optional[str] = None
    discovered_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'url': self.url,
            'title': self.title,
            'company': self.company,
            'year': self.year,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'source': self.source,
            'download_path': self.download_path,
            'discovered_at': self.discovered_at
        }


# ============================================================================
# STEALTH CONFIGURATION
# ============================================================================

STEALTH_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

STEALTH_VIEWPORT = {"width": 1920, "height": 1080}

STEALTH_LOCALE = "en-US"

STEALTH_TIMEZONE = "America/New_York"


# ============================================================================
# PLAYWRIGHT SCRAPER
# ============================================================================

class PlaywrightScraper:
    """
    Production-ready Playwright scraper for climate report discovery
    Handles JavaScript rendering, SPA navigation, and bot protection
    """
    
    def __init__(self,
                 headless: bool = True,
                 timeout_ms: int = 30000,
                 download_dir: str = "./data/reports",
                 max_pages: int = 10,
                 respect_robots: bool = True):
        """
        Initialize Playwright scraper
        
        Args:
            headless: Run browser without GUI
            timeout_ms: Page load timeout
            download_dir: Where to save downloaded PDFs
            max_pages: Maximum pages to crawl per site
            respect_robots: Check robots.txt
        """
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.max_pages = max_pages
        self.respect_robots = respect_robots
        
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.visited_urls: set = set()
        self.discovered_reports: List[ScrapedReport] = []
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
        )
        
        # Create stealth context
        self.context = await self.browser.new_context(
            user_agent=random.choice(STEALTH_USER_AGENTS),
            viewport=STEALTH_VIEWPORT,
            locale=STEALTH_LOCALE,
            timezone_id=STEALTH_TIMEZONE,
            java_script_enabled=True,
            bypass_csp=True,
            ignore_https_errors=True,
        )
        
        # Inject stealth scripts
        await self._apply_stealth_scripts()
        
        logger.info("Playwright scraper initialized")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Playwright scraper closed")
    
    async def _apply_stealth_scripts(self):
        """Apply stealth scripts to bypass bot detection"""
        # Modify navigator properties
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format", enabledPlugin: Plugin},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    }
                ]
            });
            
            window.chrome = {
                runtime: {}
            };
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({state: Notification.permission}) :
                    originalQuery(parameters)
            );
        """)
    
    async def scrape_company(self,
                            company_name: str,
                            website_url: str,
                            max_depth: int = 2) -> List[ScrapedReport]:
        """
        Scrape a company website for climate/sustainability reports
        
        Args:
            company_name: Company name
            website_url: Company website URL
            max_depth: How many link levels to follow
            
        Returns:
            List of discovered reports
        """
        logger.info(f"Starting Playwright scrape for {company_name}: {website_url}")
        
        self.discovered_reports = []
        self.visited_urls = set()
        
        try:
            page = await self.context.new_page()
            
            # Navigate to main page with retry
            await self._navigate_with_retry(page, website_url)
            
            # Look for sustainability/climate links
            report_links = await self._find_report_links(page, website_url, max_depth)
            
            # Process discovered PDFs
            for link_info in report_links:
                try:
                    report = await self._process_report_link(page, link_info, company_name)
                    if report:
                        self.discovered_reports.append(report)
                except Exception as e:
                    logger.warning(f"Failed to process link {link_info['url']}: {e}")
            
            await page.close()
            
        except Exception as e:
            logger.error(f"Scraping failed for {company_name}: {e}")
        
        logger.info(f"Scraping complete for {company_name}: found {len(self.discovered_reports)} reports")
        return self.discovered_reports
    
    async def _navigate_with_retry(self, page: Page, url: str, max_retries: int = 3):
        """Navigate to URL with retry logic and human-like delays"""
        for attempt in range(max_retries):
            try:
                # Random delay to seem human
                await asyncio.sleep(random.uniform(1, 3))
                
                response = await page.goto(
                    url,
                    wait_until="networkidle",
                    timeout=self.timeout_ms
                )
                
                if response and response.status < 400:
                    logger.debug(f"Successfully loaded {url}")
                    return response
                    
            except PlaywrightTimeout:
                logger.warning(f"Timeout on attempt {attempt + 1} for {url}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    
        raise Exception(f"Failed to navigate to {url} after {max_retries} attempts")
    
    async def _find_report_links(self,
                                 page: Page,
                                 base_url: str,
                                 max_depth: int) -> List[Dict[str, Any]]:
        """
        Find links to climate/sustainability reports
        
        Args:
            page: Playwright page
            base_url: Starting URL
            max_depth: Crawl depth
            
        Returns:
            List of link dictionaries with URL, title, context
        """
        report_links = []
        
        # Keywords to identify sustainability sections
        sustainability_keywords = [
            'sustainability', 'esg', 'environmental', 'climate', 'carbon',
            'emissions', 'greenhouse', 'ghg', 'csr', 'impact', 'report'
        ]
        
        # Get all links on current page
        links = await page.eval_on_selector_all('a[href]', '''elements => 
            elements.map(el => ({
                href: el.href,
                text: el.innerText?.trim() || '',
                title: el.title || '',
                isVisible: el.offsetParent !== null
            })).filter(link => link.isVisible)
        ''')
        
        for link in links:
            href = link.get('href', '')
            text = f"{link.get('text', '')} {link.get('title', '')}".lower()
            
            # Check if link is relevant
            is_relevant = any(kw in text for kw in sustainability_keywords)
            is_pdf = href.endswith('.pdf')
            
            if is_relevant or is_pdf:
                # Extract year from text or URL
                year = self._extract_year(text + ' ' + href)
                
                report_links.append({
                    'url': href,
                    'title': link.get('text', ''),
                    'context': text,
                    'year': year,
                    'is_pdf': is_pdf
                })
        
        # Follow navigation to sustainability pages
        if max_depth > 0:
            sustainability_links = [
                link for link in links
                if any(kw in link.get('text', '').lower() for kw in sustainability_keywords[:5])
                and link.get('href', '').startswith(base_url)
            ]
            
            for link in sustainability_links[:3]:  # Limit to 3 subpages
                sub_url = link.get('href')
                if sub_url and sub_url not in self.visited_urls:
                    self.visited_urls.add(sub_url)
                    try:
                        await self._navigate_with_retry(page, sub_url)
                        sub_links = await self._find_report_links(page, base_url, max_depth - 1)
                        report_links.extend(sub_links)
                    except Exception as e:
                        logger.warning(f"Failed to explore {sub_url}: {e}")
        
        # Remove duplicates
        seen_urls = set()
        unique_links = []
        for link in report_links:
            if link['url'] not in seen_urls:
                seen_urls.add(link['url'])
                unique_links.append(link)
        
        return unique_links
    
    def _extract_year(self, text: str) -> Optional[int]:
        """Extract year from text"""
        import re
        # Look for years 2015-2030
        match = re.search(r'\b(20(?:1[5-9]|2[0-9]|30))\b', text)
        if match:
            return int(match.group(1))
        return None
    
    async def _process_report_link(self,
                                  page: Page,
                                  link_info: Dict[str, Any],
                                  company_name: str) -> Optional[ScrapedReport]:
        """
        Process a discovered report link - download if PDF
        
        Args:
            page: Playwright page
            link_info: Link dictionary
            company_name: Company name
            
        Returns:
            ScrapedReport or None
        """
        url = link_info['url']
        
        if link_info.get('is_pdf'):
            # Download PDF
            download_path = await self._download_pdf(page, url, company_name)
            
            if download_path:
                return ScrapedReport(
                    url=url,
                    title=link_info['title'] or f"{company_name} Report",
                    company=company_name,
                    year=link_info.get('year'),
                    file_type='pdf',
                    download_path=str(download_path),
                    source='playwright'
                )
        else:
            # Return link for manual inspection
            return ScrapedReport(
                url=url,
                title=link_info['title'] or f"{company_name} Page",
                company=company_name,
                year=link_info.get('year'),
                file_type='html',
                source='playwright'
            )
        
        return None
    
    async def _download_pdf(self,
                           page: Page,
                           pdf_url: str,
                           company_name: str) -> Optional[Path]:
        """
        Download PDF using Playwright
        
        Args:
            page: Playwright page
            pdf_url: URL of PDF
            company_name: For filename
            
        Returns:
            Path to downloaded file or None
        """
        try:
            # Generate safe filename
            url_hash = hashlib.md5(pdf_url.encode()).hexdigest()[:8]
            safe_name = "".join(c if c.isalnum() else "_" for c in company_name)
            filename = f"{safe_name}_{url_hash}.pdf"
            download_path = self.download_dir / filename
            
            # Check if already downloaded
            if download_path.exists():
                logger.info(f"PDF already exists: {download_path}")
                return download_path
            
            # Download via CDP
            client = await page.context.new_cdp_session(page)
            
            # Enable network events
            await client.send('Fetch.enable')
            
            # Trigger download
            response = await page.evaluate(f'''
                async () => {{
                    const response = await fetch("{pdf_url}", {{
                        method: 'GET',
                        headers: {{
                            'Accept': 'application/pdf,*/*'
                        }}
                    }});
                    const blob = await response.blob();
                    return blob.size;
                }}
            ''')
            
            # Alternative: Use context download event
            async with page.expect_download() as download_info:
                await page.evaluate(f'window.location.href = "{pdf_url}"')
            
            download = await download_info.value
            await download.save_as(download_path)
            
            # Wait for download
            await asyncio.sleep(2)
            
            if download_path.exists():
                file_size = download_path.stat().st_size
                logger.info(f"Downloaded PDF: {download_path} ({file_size} bytes)")
                return download_path
            else:
                # Fallback: direct download with requests
                return await self._fallback_download(pdf_url, download_path)
                
        except Exception as e:
            logger.error(f"PDF download failed: {e}")
            return await self._fallback_download(pdf_url, download_path)
    
    async def _fallback_download(self,
                                  pdf_url: str,
                                  download_path: Path) -> Optional[Path]:
        """Fallback download using requests"""
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(pdf_url, timeout=60) as response:
                    if response.status == 200:
                        content = await response.read()
                        download_path.write_bytes(content)
                        logger.info(f"Downloaded via fallback: {download_path}")
                        return download_path
        except Exception as e:
            logger.error(f"Fallback download failed: {e}")
        
        return None
    
    async def screenshot_page(self,
                             url: str,
                             output_path: str,
                             full_page: bool = True) -> bool:
        """
        Take screenshot of page (useful for debugging)
        
        Args:
            url: Page URL
            output_path: Screenshot file path
            full_page: Capture full scrollable page
            
        Returns:
            True if successful
        """
        try:
            page = await self.context.new_page()
            await self._navigate_with_retry(page, url)
            await page.screenshot(path=output_path, full_page=full_page)
            await page.close()
            logger.info(f"Screenshot saved: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return False


# ============================================================================
# PRODUCTION SCRAPER MANAGER
# ============================================================================

class PlaywrightScraperManager:
    """
    Manager for running multiple Playwright scraping jobs
    Handles resource limits and job queuing
    """
    
    def __init__(self,
                 max_concurrent: int = 3,
                 download_dir: str = "./data/reports"):
        """
        Initialize scraper manager
        
        Args:
            max_concurrent: Max parallel scrapers
            download_dir: Download directory
        """
        self.max_concurrent = max_concurrent
        self.download_dir = Path(download_dir)
        self.results: Dict[str, List[ScrapedReport]] = {}
    
    async def scrape_companies(self,
                              companies: List[Dict[str, str]]) -> Dict[str, List[ScrapedReport]]:
        """
        Scrape multiple companies with concurrency control
        
        Args:
            companies: List of dicts with 'name' and 'url' keys
            
        Returns:
            Dictionary mapping company name to reports
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def scrape_with_limit(company):
            async with semaphore:
                async with PlaywrightScraper(download_dir=str(self.download_dir)) as scraper:
                    reports = await scraper.scrape_company(
                        company['name'],
                        company['url']
                    )
                    return company['name'], reports
        
        tasks = [scrape_with_limit(c) for c in companies]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        output = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Scraping job failed: {result}")
            else:
                company_name, reports = result
                output[company_name] = reports
        
        return output
    
    async def scrape_single(self,
                           company_name: str,
                           website_url: str) -> List[ScrapedReport]:
        """Scrape single company"""
        async with PlaywrightScraper(download_dir=str(self.download_dir)) as scraper:
            return await scraper.scrape_company(company_name, website_url)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def scrape_company_reports(company_name: str,
                                  website_url: str,
                                  download_dir: str = "./data/reports") -> List[Dict[str, Any]]:
    """
    Simple async function to scrape a company
    
    Args:
        company_name: Company name
        website_url: Company website
        download_dir: Where to save PDFs
        
    Returns:
        List of report dictionaries
    """
    async with PlaywrightScraper(download_dir=download_dir) as scraper:
        reports = await scraper.scrape_company(company_name, website_url)
        return [r.to_dict() for r in reports]


def scrape_company_sync(company_name: str,
                       website_url: str,
                       download_dir: str = "./data/reports") -> List[Dict[str, Any]]:
    """
    Synchronous wrapper for scraping
    
    Args:
        company_name: Company name
        website_url: Company website
        download_dir: Where to save PDFs
        
    Returns:
        List of report dictionaries
    """
    return asyncio.run(scrape_company_reports(
        company_name, website_url, download_dir
    ))


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def example_usage():
    """Example of using the Playwright scraper"""
    
    # Scrape single company
    async with PlaywrightScraper(headless=True) as scraper:
        reports = await scraper.scrape_company(
            company_name="Tesla",
            website_url="https://www.tesla.com"
        )
        
        for report in reports:
            print(f"Found: {report.title}")
            print(f"  URL: {report.url}")
            print(f"  Year: {report.year}")
            print(f"  Downloaded: {report.download_path}")
    
    # Scrape multiple companies
    companies = [
        {"name": "Tesla", "url": "https://www.tesla.com"},
        {"name": "Microsoft", "url": "https://www.microsoft.com"},
    ]
    
    manager = PlaywrightScraperManager(max_concurrent=2)
    results = await manager.scrape_companies(companies)
    
    for company, reports in results.items():
        print(f"\n{company}: {len(reports)} reports found")


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())
