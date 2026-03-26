"""
Climate Data Extraction System - PDF Parse Module

Provides tools for parsing PDFs and extracting emissions data.
"""

from .pdf_parser import (
    PDFParser,
    PDFTextExtractor,
    EmissionsPatternMatcher,
    EmissionsData,
    parse_pdf,
    parse_pdfs,
    extract_to_json,
)

__all__ = [
    'PDFParser',
    'PDFTextExtractor',
    'EmissionsPatternMatcher',
    'EmissionsData',
    'parse_pdf',
    'parse_pdfs',
    'extract_to_json',
]
