"""
Climate Data Extraction - Streamlined Main System
Clean architecture: Discovery -> Download -> Extract -> Store
"""

import os
import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

from climate_extract.discover.google_discovery import UnifiedDiscovery, DiscoveredReport
from climate_extract.extractors.hybrid_extractor import HybridExtractor, ExtractedEmissionsData
from climate_extract.core.database import DatabaseRepository
from climate_extract.core.config import settings
from climate_extract.utils.logging import get_logger

logger = get_logger(__name__)


class ClimateExtractor:
    """
    Main extraction system - clean and focused

    Flow: Company -> Discover PDFs -> Download -> Extract Emissions -> Store
    """

    def __init__(self,
                 output_dir: str = "./data",
                 use_llm: bool = False,
                 use_playwright: bool = False):
        """
        Initialize the extractor

        Args:
            output_dir: Directory for downloads and outputs
            use_llm: Enable LLM fallback for extraction (requires API key)
            use_playwright: Enable Playwright for JS websites (slower)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.reports_dir = self.output_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)

        self.discovery = UnifiedDiscovery(str(self.reports_dir))

        # Initialize extractor
        llm_extractor = None
        if use_llm:
            try:
                from climate_extract.extractors.llm_extractor import LLMExtractor
                llm_extractor = LLMExtractor()
                if llm_extractor.client:
                    logger.info("LLM extractor enabled")
            except Exception as e:
                logger.warning(f"LLM extractor not available: {e}")

        self.extractor = HybridExtractor(llm_extractor=llm_extractor)
        self.use_playwright = use_playwright

        # Database (optional)
        try:
            self.db = DatabaseRepository()
            logger.info("Database connected")
        except Exception as e:
            logger.warning(f"Database not available: {e}")
            self.db = None

    def extract_company(self,
                       company_name: str,
                       website: Optional[str] = None,
                       max_reports: int = 5) -> Dict[str, Any]:
        """
        Extract climate data for a single company

        Args:
            company_name: Company name (e.g., "Tesla", "Microsoft")
            website: Optional company website URL
            max_reports: Maximum reports to process

        Returns:
            Extraction results dictionary
        """
        start_time = time.time()

        result = {
            "company": company_name,
            "website": website,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "started",
            "reports_found": 0,
            "reports_downloaded": 0,
            "reports_extracted": 0,
            "emissions_data": [],
            "errors": []
        }

        logger.info("=" * 60)
        logger.info(f"EXTRACTING: {company_name}")
        logger.info("=" * 60)

        try:
            # Step 1: Discover reports
            logger.info("Step 1: Discovering reports...")
            reports = self.discovery.discover_reports(
                company_name=company_name,
                website=website,
                max_reports=max_reports,
                use_playwright=self.use_playwright
            )

            result["reports_found"] = len(reports)

            if not reports:
                result["status"] = "no_reports_found"
                result["errors"].append("No PDF reports discovered")
                logger.warning(f"No reports found for {company_name}")
                return result

            logger.info(f"Found {len(reports)} reports")

            # Step 2: Download reports
            logger.info("Step 2: Downloading reports...")
            downloaded = []

            for i, report in enumerate(reports, 1):
                logger.info(f"  [{i}/{len(reports)}] {report.title[:50]}...")

                filepath = self.discovery.download_report(report, company_name)
                if filepath:
                    downloaded.append((report, filepath))

                time.sleep(1)  # Rate limit

            result["reports_downloaded"] = len(downloaded)

            if not downloaded:
                result["status"] = "download_failed"
                result["errors"].append("All downloads failed")
                return result

            logger.info(f"Downloaded {len(downloaded)} reports")

            # Step 3: Extract emissions data
            logger.info("Step 3: Extracting emissions data...")

            for report, filepath in downloaded:
                try:
                    extracted = self.extractor.extract(str(filepath), report.year)

                    if self._has_emissions_data(extracted):
                        emissions_dict = self._to_dict(extracted, report)
                        result["emissions_data"].append(emissions_dict)
                        result["reports_extracted"] += 1

                        # Save to database if available
                        if self.db:
                            self._save_to_db(company_name, report, extracted)

                except Exception as e:
                    logger.error(f"Extraction failed for {filepath}: {e}")
                    result["errors"].append(f"{filepath}: {str(e)}")

            # Final status
            if result["reports_extracted"] > 0:
                result["status"] = "success"
            else:
                result["status"] = "extraction_failed"

        except Exception as e:
            logger.error(f"Processing failed: {e}")
            result["status"] = "error"
            result["errors"].append(str(e))

        result["duration_seconds"] = round(time.time() - start_time, 2)

        logger.info("=" * 60)
        logger.info(f"RESULT: {result['status']} - {result['reports_extracted']}/{result['reports_found']} extracted")
        logger.info("=" * 60)

        return result

    def extract_batch(self,
                     companies: List[Dict[str, str]],
                     max_reports_per_company: int = 5) -> Dict[str, Any]:
        """
        Extract data for multiple companies

        Args:
            companies: List of {"name": "...", "website": "..."} dicts
            max_reports_per_company: Max reports per company

        Returns:
            Batch results dictionary
        """
        start_time = time.time()

        batch_result = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_companies": len(companies),
            "successful": 0,
            "failed": 0,
            "results": []
        }

        logger.info(f"Starting batch extraction for {len(companies)} companies")

        for i, company_info in enumerate(companies, 1):
            name = company_info.get("name", "")
            website = company_info.get("website")

            logger.info(f"\n[{i}/{len(companies)}] Processing: {name}")

            try:
                result = self.extract_company(
                    company_name=name,
                    website=website,
                    max_reports=max_reports_per_company
                )

                batch_result["results"].append(result)

                if result["status"] == "success":
                    batch_result["successful"] += 1
                else:
                    batch_result["failed"] += 1

            except Exception as e:
                logger.error(f"Failed to process {name}: {e}")
                batch_result["failed"] += 1
                batch_result["results"].append({
                    "company": name,
                    "status": "error",
                    "error": str(e)
                })

            # Rate limit between companies
            if i < len(companies):
                time.sleep(3)

        batch_result["duration_seconds"] = round(time.time() - start_time, 2)

        logger.info(f"\nBatch complete: {batch_result['successful']}/{batch_result['total_companies']} successful")

        return batch_result

    def _has_emissions_data(self, data: ExtractedEmissionsData) -> bool:
        """Check if extracted data has any emissions values"""
        return any([
            data.scope_1_absolute,
            data.scope_2_location_based,
            data.scope_2_market_based,
            data.scope_3_total,
            data.total_emissions
        ])

    def _to_dict(self, data: ExtractedEmissionsData, report: DiscoveredReport) -> Dict:
        """Convert extracted data to dictionary"""
        return {
            "source_url": report.url,
            "source_title": report.title,
            "year": data.reporting_year or report.year,
            "scope_1": data.scope_1_absolute,
            "scope_2_location": data.scope_2_location_based,
            "scope_2_market": data.scope_2_market_based,
            "scope_3": data.scope_3_total,
            "total_emissions": data.total_emissions,
            "unit": "tCO2e",
            "confidence": data.confidence_score,
            "extraction_method": data.extraction_method
        }

    def _save_to_db(self, company_name: str, report: DiscoveredReport, data: ExtractedEmissionsData):
        """Save extracted data to database"""
        try:
            company = self.db.get_or_create_company(name=company_name)

            # Create report record
            report_record = self.db.create_report(
                company_id=company.id,
                report_year=data.reporting_year or report.year or datetime.now().year,
                report_type='sustainability',
                source_url=report.url,
                title=report.title,
                local_path=report.local_path
            )

            # Create emissions record
            self.db.create_emissions_record(
                company_id=company.id,
                report_id=report_record.id,
                reporting_year=data.reporting_year or report.year,
                scope_1=data.scope_1_absolute,
                scope_2_location=data.scope_2_location_based,
                scope_2_market=data.scope_2_market_based,
                scope_3_total=data.scope_3_total,
                total_emissions=data.total_emissions
            )

            logger.info(f"Saved to database: {company_name} {report.year}")

        except Exception as e:
            logger.error(f"Database save failed: {e}")


# Convenience functions for simple usage

def extract_single(company_name: str,
                   website: Optional[str] = None,
                   max_reports: int = 5,
                   output_dir: str = "./data") -> Dict[str, Any]:
    """
    Simple function to extract data for one company

    Example:
        result = extract_single("Tesla", website="https://tesla.com")
        print(result["emissions_data"])
    """
    extractor = ClimateExtractor(output_dir=output_dir)
    return extractor.extract_company(company_name, website, max_reports)


def extract_batch(companies: List[Dict[str, str]],
                  output_file: Optional[str] = None,
                  output_dir: str = "./data") -> Dict[str, Any]:
    """
    Extract data for multiple companies

    Example:
        companies = [
            {"name": "Tesla", "website": "https://tesla.com"},
            {"name": "Microsoft", "website": "https://microsoft.com"},
        ]
        result = extract_batch(companies, output_file="results.json")
    """
    extractor = ClimateExtractor(output_dir=output_dir)
    result = extractor.extract_batch(companies)

    if output_file:
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        logger.info(f"Results saved to {output_file}")

    return result


if __name__ == "__main__":
    # Quick test
    result = extract_single("Tesla", max_reports=2)
    print(json.dumps(result, indent=2, default=str))
