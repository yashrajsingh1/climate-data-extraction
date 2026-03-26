"""
Climate Data Extraction System

AI-powered extraction of emissions data from company sustainability reports.

Quick Start:
    from climate_extract import extract_company, extract_batch

    # Single company
    result = extract_company("Tesla")

    # Multiple companies
    results = extract_batch([
        {"name": "Tesla", "website": "https://tesla.com"},
        {"name": "Microsoft", "website": "https://microsoft.com"}
    ])

CLI Usage:
    python run.py Tesla
    python run.py --batch companies.json --output results.json
"""

from climate_extract.main import (
    ClimateExtractor,
    extract_single as extract_company,
    extract_batch
)

__version__ = "2.0.0"
__all__ = ["ClimateExtractor", "extract_company", "extract_batch"]
