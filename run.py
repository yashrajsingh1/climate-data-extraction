#!/usr/bin/env python3
"""
Climate Data Extraction - Command Line Interface
Simple, focused CLI for extracting climate data from company reports
"""

import sys
import json
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Climate Data Extraction System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract data for a single company
  python run.py Tesla
  python run.py Tesla --website https://tesla.com

  # Extract with more reports
  python run.py Microsoft --max 10

  # Batch extraction from file
  python run.py --batch companies.json --output results.json

  # Show help
  python run.py --help

Required Setup:
  1. Set environment variables:
     GOOGLE_API_KEY=your_google_api_key
     GOOGLE_CSE_ID=your_custom_search_engine_id

  2. Get free API key from:
     https://developers.google.com/custom-search/v1/introduction
        """
    )

    parser.add_argument(
        "company",
        nargs="?",
        help="Company name to extract (e.g., Tesla, Microsoft)"
    )

    parser.add_argument(
        "--website", "-w",
        help="Company website URL (optional)"
    )

    parser.add_argument(
        "--max", "-m",
        type=int,
        default=5,
        help="Maximum reports to process (default: 5)"
    )

    parser.add_argument(
        "--batch", "-b",
        help="JSON file with list of companies for batch extraction"
    )

    parser.add_argument(
        "--output", "-o",
        help="Output file for results (JSON)"
    )

    parser.add_argument(
        "--data-dir", "-d",
        default="./data",
        help="Directory for downloads and outputs (default: ./data)"
    )

    parser.add_argument(
        "--playwright", "-p",
        action="store_true",
        help="Enable Playwright for JavaScript-heavy websites (slower)"
    )

    parser.add_argument(
        "--llm",
        action="store_true",
        help="Enable LLM fallback extraction (requires OPENAI_API_KEY)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)

    # Validate arguments
    if not args.company and not args.batch:
        parser.print_help()
        print("\nError: Please provide a company name or --batch file")
        sys.exit(1)

    # Import here to avoid slow startup for --help
    from climate_extract.main import ClimateExtractor

    # Initialize extractor
    extractor = ClimateExtractor(
        output_dir=args.data_dir,
        use_llm=args.llm,
        use_playwright=args.playwright
    )

    # Run extraction
    if args.batch:
        # Batch mode
        batch_file = Path(args.batch)
        if not batch_file.exists():
            print(f"Error: Batch file not found: {args.batch}")
            sys.exit(1)

        with open(batch_file) as f:
            companies = json.load(f)

        if not isinstance(companies, list):
            print("Error: Batch file must contain a JSON array of companies")
            sys.exit(1)

        result = extractor.extract_batch(companies, args.max)

    else:
        # Single company mode
        result = extractor.extract_company(
            company_name=args.company,
            website=args.website,
            max_reports=args.max
        )

    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\nResults saved to: {args.output}")
    else:
        # Print summary to console
        print_summary(result, args.batch is not None)


def print_summary(result: dict, is_batch: bool):
    """Print a nice summary of results"""
    print("\n" + "=" * 60)
    print("EXTRACTION RESULTS")
    print("=" * 60)

    if is_batch:
        print(f"Total companies: {result.get('total_companies', 0)}")
        print(f"Successful: {result.get('successful', 0)}")
        print(f"Failed: {result.get('failed', 0)}")
        print(f"Duration: {result.get('duration_seconds', 0)}s")

        for company_result in result.get('results', []):
            status = company_result.get('status', 'unknown')
            name = company_result.get('company', 'Unknown')
            extracted = len(company_result.get('emissions_data', []))
            print(f"  - {name}: {status} ({extracted} records)")

    else:
        print(f"Company: {result.get('company', 'Unknown')}")
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Reports found: {result.get('reports_found', 0)}")
        print(f"Reports downloaded: {result.get('reports_downloaded', 0)}")
        print(f"Reports extracted: {result.get('reports_extracted', 0)}")
        print(f"Duration: {result.get('duration_seconds', 0)}s")

        emissions = result.get('emissions_data', [])
        if emissions:
            print("\nEmissions Data:")
            for e in emissions:
                year = e.get('year', '?')
                s1 = e.get('scope_1', '-')
                s2 = e.get('scope_2_location', '-')
                s3 = e.get('scope_3', '-')
                conf = e.get('confidence', 0)
                print(f"  Year {year}:")
                print(f"    Scope 1: {s1}")
                print(f"    Scope 2: {s2}")
                print(f"    Scope 3: {s3}")
                print(f"    Confidence: {conf:.1%}")

        errors = result.get('errors', [])
        if errors:
            print("\nErrors:")
            for err in errors[:5]:
                print(f"  - {err}")

    print("=" * 60)


if __name__ == "__main__":
    main()
