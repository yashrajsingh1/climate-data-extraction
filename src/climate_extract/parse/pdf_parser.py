"""
Climate Data Extraction System - PDF Parsing Module
Extracts structured emissions data from sustainability report PDFs
"""

import re
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class EmissionsData:
    """Structured emissions data extracted from PDF"""
    company: str = ""
    year: str = ""
    scope_1: str = ""
    scope_2: str = ""
    scope_3: str = ""
    total_emissions: str = ""
    unit: str = ""
    confidence: float = 0.0
    extraction_method: str = ""
    raw_snippets: Dict[str, str] = None
    
    def __post_init__(self):
        if self.raw_snippets is None:
            self.raw_snippets = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class PDFTextExtractor:
    """Extract text from PDF files using PyMuPDF or pdfminer"""
    
    def __init__(self, max_pages: int = 500):
        """
        Initialize text extractor
        
        Args:
            max_pages: Maximum number of pages to process
        """
        self.max_pages = max_pages
    
    def extract_with_pymupdf(self, pdf_path: Path) -> str:
        """
        Extract text using PyMuPDF (fitz)
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text
        """
        try:
            import fitz
            
            text = ""
            doc = fitz.open(str(pdf_path))
            
            for page_num in range(min(len(doc), self.max_pages)):
                page = doc[page_num]
                text += page.get_text() + "\n"
            
            doc.close()
            logger.info(f"Extracted text from {pdf_path} using PyMuPDF")
            return text
            
        except ImportError:
            logger.error("PyMuPDF not installed. Install with: pip install PyMuPDF")
            raise
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed: {e}")
            raise
    
    def extract_with_pdfminer(self, pdf_path: Path) -> str:
        """
        Extract text using pdfminer.six (fallback)
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text
        """
        try:
            from pdfminer.high_level import extract_text
            
            text = extract_text(str(pdf_path), maxpages=self.max_pages)
            logger.info(f"Extracted text from {pdf_path} using pdfminer")
            return text
            
        except ImportError:
            logger.error("pdfminer.six not installed. Install with: pip install pdfminer.six")
            raise
        except Exception as e:
            logger.error(f"pdfminer extraction failed: {e}")
            raise
    
    def extract(self, pdf_path: Path, method: str = "auto") -> str:
        """
        Extract text from PDF using specified method
        
        Args:
            pdf_path: Path to PDF file
            method: Extraction method - "pymupdf", "pdfminer", or "auto"
            
        Returns:
            Extracted text
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        if method == "pymupdf":
            return self.extract_with_pymupdf(pdf_path)
        elif method == "pdfminer":
            return self.extract_with_pdfminer(pdf_path)
        elif method == "auto":
            # Try PyMuPDF first, fallback to pdfminer
            try:
                return self.extract_with_pymupdf(pdf_path)
            except Exception:
                logger.warning("PyMuPDF failed, trying pdfminer")
                return self.extract_with_pdfminer(pdf_path)
        else:
            raise ValueError(f"Unknown extraction method: {method}")


class EmissionsPatternMatcher:
    """Pattern matching for emissions data using regex"""
    
    def __init__(self):
        """Initialize emission patterns"""
        self.patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Compile regex patterns for emission extraction"""
        
        # Number patterns (handles commas, decimals, millions, etc.)
        number = r'[\d,]+(?:\.\d+)?'
        
        # Unit patterns
        units = r'(?:tCO2e|tCO₂e|t CO2e|tonnes? CO2e?|metric tons? CO2e?|MtCO2e|million tonnes?)'
        
        patterns = {
            'scope_1': [
                # Standard formats
                re.compile(r'[Ss]cope\s*1[^0-9]{0,50}(' + number + r')\s*(?:' + units + r')?', re.IGNORECASE | re.DOTALL),
                re.compile(r'[Ss]cope\s*one[^0-9]{0,50}(' + number + r')\s*(?:' + units + r')?', re.IGNORECASE | re.DOTALL),
                # Direct emissions
                re.compile(r'[Dd]irect\s*emissions[^0-9]{0,50}(' + number + r')\s*(?:' + units + r')?', re.IGNORECASE | re.DOTALL),
                # Stationary combustion
                re.compile(r'[Ss]tationary\s*combustion[^0-9]{0,50}(' + number + r')\s*(?:' + units + r')?', re.IGNORECASE | re.DOTALL),
                # Mobile combustion
                re.compile(r'[Mm]obile\s*combustion[^0-9]{0,50}(' + number + r')\s*(?:' + units + r')?', re.IGNORECASE | re.DOTALL),
                # Table format
                re.compile(r'Scope\s*1[\s\w%]{0,100}?(' + number + r')\s*(?:' + units + r')?\s*$', re.IGNORECASE | re.MULTILINE),
            ],
            'scope_2': [
                # Standard formats
                re.compile(r'[Ss]cope\s*2[^0-9]{0,50}(' + number + r')\s*(?:' + units + r')?', re.IGNORECASE | re.DOTALL),
                re.compile(r'[Ss]cope\s*two[^0-9]{0,50}(' + number + r')\s*(?:' + units + r')?', re.IGNORECASE | re.DOTALL),
                # Indirect emissions
                re.compile(r'[Ii]ndirect\s*emissions[^0-9]{0,50}(' + number + r')\s*(?:' + units + r')?', re.IGNORECASE | re.DOTALL),
                # Location-based
                re.compile(r'[Ll]ocation[- ]?based[^0-9]{0,50}(' + number + r')\s*(?:' + units + r')?', re.IGNORECASE | re.DOTALL),
                # Market-based
                re.compile(r'[Mm]arket[- ]?based[^0-9]{0,50}(' + number + r')\s*(?:' + units + r')?', re.IGNORECASE | re.DOTALL),
                # Table format
                re.compile(r'Scope\s*2[\s\w%]{0,100}?(' + number + r')\s*(?:' + units + r')?\s*$', re.IGNORECASE | re.MULTILINE),
            ],
            'scope_3': [
                # Standard formats
                re.compile(r'[Ss]cope\s*3[^0-9]{0,50}(' + number + r')\s*(?:' + units + r')?', re.IGNORECASE | re.DOTALL),
                re.compile(r'[Ss]cope\s*three[^0-9]{0,50}(' + number + r')\s*(?:' + units + r')?', re.IGNORECASE | re.DOTALL),
                # Value chain
                re.compile(r'[Vv]alue\s*chain\s*emissions[^0-9]{0,50}(' + number + r')\s*(?:' + units + r')?', re.IGNORECASE | re.DOTALL),
                # Other indirect
                re.compile(r'[Oo]ther\s*indirect\s*emissions[^0-9]{0,50}(' + number + r')\s*(?:' + units + r')?', re.IGNORECASE | re.DOTALL),
                # Upstream and downstream
                re.compile(r'[Uu]pstream[^0-9]{0,50}(' + number + r')\s*(?:' + units + r')?', re.IGNORECASE | re.DOTALL),
                re.compile(r'[Dd]ownstream[^0-9]{0,50}(' + number + r')\s*(?:' + units + r')?', re.IGNORECASE | re.DOTALL),
                # Table format
                re.compile(r'Scope\s*3[\s\w%]{0,100}?(' + number + r')\s*(?:' + units + r')?\s*$', re.IGNORECASE | re.MULTILINE),
            ],
            'total_emissions': [
                re.compile(r'[Tt]otal\s*emissions[^0-9]{0,50}(' + number + r')\s*(?:' + units + r')?', re.IGNORECASE | re.DOTALL),
                re.compile(r'[Tt]otal\s*GHG[^0-9]{0,50}(' + number + r')\s*(?:' + units + r')?', re.IGNORECASE | re.DOTALL),
                re.compile(r'[Gg]ross\s*emissions[^0-9]{0,50}(' + number + r')\s*(?:' + units + r')?', re.IGNORECASE | re.DOTALL),
                re.compile(r'[Tt]otal\s*carbon[^0-9]{0,50}(' + number + r')\s*(?:' + units + r')?', re.IGNORECASE | re.DOTALL),
            ],
            'unit': [
                re.compile(r'(' + units + r')', re.IGNORECASE),
            ],
            'year': [
                # Reporting year patterns
                re.compile(r'[Rr]eporting\s*[Yy]ear\s*(\d{4})', re.IGNORECASE),
                re.compile(r'[Ff]iscal\s*[Yy]ear\s*(\d{4})', re.IGNORECASE),
                re.compile(r'FY\s*(\d{4})', re.IGNORECASE),
                re.compile(r'[Aa]nnual\s*[Rr]eport\s*(\d{4})', re.IGNORECASE),
                re.compile(r'[Ss]ustainability\s*[Rr]eport\s*(\d{4})', re.IGNORECASE),
                re.compile(r'(\d{4})\s*[Ss]ustainability', re.IGNORECASE),
                re.compile(r'(?:January|February|March|April|May|June|July|August|September|October|November|December),?\s+(\d{4})', re.IGNORECASE),
            ],
            'company': [
                # Company name patterns (from title/cover)
                re.compile(r'^\s*([A-Z][A-Za-z0-9\s&.,]+?)(?:\s*-|\s*Annual|\s*Sustainability|\s*ESG|\s*Report|\s*\d{4})', re.MULTILINE),
            ]
        }
        
        return patterns
    
    def extract_value(self, text: str, field: str) -> Tuple[str, str]:
        """
        Extract value for a specific field
        
        Args:
            text: Full text to search
            field: Field name (scope_1, scope_2, scope_3, total_emissions, unit, year, company)
            
        Returns:
            Tuple of (extracted_value, raw_snippet)
        """
        if field not in self.patterns:
            return "", ""
        
        for pattern in self.patterns[field]:
            matches = pattern.findall(text)
            if matches:
                # Get first match
                match = matches[0]
                if isinstance(match, tuple):
                    match = match[0]
                
                # Clean the extracted value
                value = match.strip().replace(',', '')
                
                # Get surrounding text for snippet
                snippet_match = pattern.search(text)
                if snippet_match:
                    start = max(0, snippet_match.start() - 50)
                    end = min(len(text), snippet_match.end() + 50)
                    snippet = text[start:end].strip()
                else:
                    snippet = ""
                
                return value, snippet
        
        return "", ""
    
    def extract_all(self, text: str) -> Dict[str, Any]:
        """
        Extract all emissions fields from text
        
        Args:
            text: Full text to search
            
        Returns:
            Dictionary with extracted values and snippets
        """
        results = {}
        
        fields = ['scope_1', 'scope_2', 'scope_3', 'total_emissions', 'unit', 'year', 'company']
        
        for field in fields:
            value, snippet = self.extract_value(text, field)
            results[field] = value
            if snippet:
                results[f'{field}_snippet'] = snippet
        
        return results


class PDFParser:
    """Main PDF parser for emissions data extraction"""
    
    def __init__(self, max_pages: int = 500):
        """
        Initialize PDF parser
        
        Args:
            max_pages: Maximum pages to process
        """
        self.text_extractor = PDFTextExtractor(max_pages=max_pages)
        self.pattern_matcher = EmissionsPatternMatcher()
    
    def parse(self, pdf_path: Path, company_name: str = "", 
              extraction_method: str = "auto") -> EmissionsData:
        """
        Parse PDF and extract emissions data
        
        Args:
            pdf_path: Path to PDF file
            company_name: Optional company name override
            extraction_method: Text extraction method (auto, pymupdf, pdfminer)
            
        Returns:
            EmissionsData object with extracted values
        """
        pdf_path = Path(pdf_path)
        logger.info(f"Parsing PDF: {pdf_path}")
        
        # Step 1: Extract text
        try:
            text = self.text_extractor.extract(pdf_path, method=extraction_method)
            actual_method = extraction_method if extraction_method != "auto" else "pymupdf/pdfminer"
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return EmissionsData(
                extraction_method="failed",
                confidence=0.0
            )
        
        # Step 2: Extract emissions data
        results = self.pattern_matcher.extract_all(text)
        
        # Step 3: Build EmissionsData object
        data = EmissionsData(
            company=company_name or results.get('company', ''),
            year=results.get('year', ''),
            scope_1=results.get('scope_1', ''),
            scope_2=results.get('scope_2', ''),
            scope_3=results.get('scope_3', ''),
            total_emissions=results.get('total_emissions', ''),
            unit=results.get('unit', ''),
            extraction_method=actual_method,
            confidence=self._calculate_confidence(results),
            raw_snippets={
                k: v for k, v in results.items() 
                if k.endswith('_snippet') and v
            }
        )
        
        logger.info(f"Extraction complete: scope_1={data.scope_1}, scope_2={data.scope_2}, scope_3={data.scope_3}")
        
        return data
    
    def parse_multiple(self, pdf_paths: List[Path], 
                       company_name: str = "") -> List[EmissionsData]:
        """
        Parse multiple PDFs
        
        Args:
            pdf_paths: List of PDF paths
            company_name: Optional company name
            
        Returns:
            List of EmissionsData objects
        """
        results = []
        for pdf_path in pdf_paths:
            try:
                data = self.parse(pdf_path, company_name)
                results.append(data)
            except Exception as e:
                logger.error(f"Failed to parse {pdf_path}: {e}")
                results.append(EmissionsData(
                    extraction_method="failed",
                    confidence=0.0
                ))
        return results
    
    def _calculate_confidence(self, results: Dict[str, Any]) -> float:
        """
        Calculate confidence score based on extraction completeness
        
        Args:
            results: Extraction results dictionary
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        score = 0.0
        
        # Check for emission values
        emission_fields = ['scope_1', 'scope_2', 'scope_3', 'total_emissions']
        found = sum(1 for f in emission_fields if results.get(f))
        score += (found / len(emission_fields)) * 0.7
        
        # Check for year
        if results.get('year'):
            score += 0.15
        
        # Check for unit
        if results.get('unit'):
            score += 0.15
        
        return round(score, 2)


# Convenience functions
def parse_pdf(pdf_path: str, company_name: str = "") -> EmissionsData:
    """
    Simple function to parse a single PDF
    
    Args:
        pdf_path: Path to PDF file
        company_name: Optional company name
        
    Returns:
        EmissionsData object
    """
    parser = PDFParser()
    return parser.parse(Path(pdf_path), company_name)


def parse_pdfs(pdf_paths: List[str], company_name: str = "") -> List[EmissionsData]:
    """
    Parse multiple PDFs
    
    Args:
        pdf_paths: List of PDF paths
        company_name: Optional company name
        
    Returns:
        List of EmissionsData objects
    """
    parser = PDFParser()
    paths = [Path(p) for p in pdf_paths]
    return parser.parse_multiple(paths, company_name)


def extract_to_json(pdf_path: str, company_name: str = "", output_path: Optional[str] = None) -> str:
    """
    Parse PDF and return/save JSON output
    
    Args:
        pdf_path: Path to PDF file
        company_name: Optional company name
        output_path: Optional path to save JSON file
        
    Returns:
        JSON string
    """
    data = parse_pdf(pdf_path, company_name)
    json_str = data.to_json()
    
    if output_path:
        Path(output_path).write_text(json_str, encoding='utf-8')
        logger.info(f"Saved JSON to: {output_path}")
    
    return json_str
