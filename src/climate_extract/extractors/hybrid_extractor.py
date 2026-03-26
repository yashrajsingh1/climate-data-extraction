"""
Climate Data Extraction System - Hybrid PDF Extraction Engine
Rule-based extraction with LLM fallback for unstructured data
"""

import re
import fitz  # PyMuPDF
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import json

from climate_extract.core.config import settings
from climate_extract.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractedEmissionsData:
    """Structured emissions data extracted from report"""
    # Scope emissions
    scope_1_absolute: Optional[float] = None
    scope_2_location_based: Optional[float] = None
    scope_2_market_based: Optional[float] = None
    scope_3_total: Optional[float] = None
    scope_3_categories: Dict[str, float] = field(default_factory=dict)
    
    # Methodologies
    scope_1_methodology: Optional[str] = None
    scope_2_methodology: Optional[str] = None
    scope_3_methodology: Optional[str] = None
    
    # Additional metrics
    total_emissions: Optional[float] = None
    renewable_energy_pct: Optional[float] = None
    energy_consumption_mwh: Optional[float] = None
    carbon_intensity: Optional[float] = None
    
    # Targets
    emission_targets: Dict[str, Any] = field(default_factory=dict)
    reduction_targets: Dict[str, Any] = field(default_factory=dict)
    
    # Verification
    third_party_verified: Optional[str] = None
    verification_standard: Optional[str] = None
    
    # Year information
    reporting_year: Optional[int] = None
    baseline_year: Optional[int] = None
    
    # Extraction metadata
    confidence_score: float = 0.0
    extraction_method: str = "unknown"
    raw_snippets: Dict[str, str] = field(default_factory=dict)


class RuleBasedExtractor:
    """Rule-based PDF extraction using regex and heuristics"""
    
    def __init__(self):
        # Emission patterns for different formats
        self.emission_patterns = {
            'scope_1': [
                # Standard formats
                r'[Ss]cope\s*1[^0-9]*?([0-9,]+\.?\d*)\s*(?:tCO2e|tCO₂e|metric tons?|tonnes?|MT|million tonnes?)',
                r'[Dd]irect emissions[^0-9]*?([0-9,]+\.?\d*)\s*(?:tCO2e|metric tons?)',
                # Table formats
                r'Scope 1[\s\w]*?(?:tCO2e)?\s*([0-9,]+\.?\d*)',
                # GHG Protocol format
                r'Category 1[\s\w]*?Stationary combustion[^0-9]*?([0-9,]+\.?\d*)',
                r'Category 2[\s\w]*?Mobile combustion[^0-9]*?([0-9,]+\.?\d*)',
            ],
            'scope_2_location': [
                r'[Ss]cope\s*2[^0-9]*?[Ll]ocation[^0-9]*?([0-9,]+\.?\d*)\s*(?:tCO2e|metric tons?)',
                r'[Ss]cope\s*2[^0-9]*?([0-9,]+\.?\d*)\s*(?:tCO2e|metric tons?)',
                r'Indirect emissions[^0-9]*?([0-9,]+\.?\d*)\s*(?:tCO2e|metric tons?)',
            ],
            'scope_2_market': [
                r'[Ss]cope\s*2[^0-9]*?[Mm]arket[^0-9]*?([0-9,]+\.?\d*)\s*(?:tCO2e|metric tons?)',
            ],
            'scope_3': [
                r'[Ss]cope\s*3[^0-9]*?([0-9,]+\.?\d*)\s*(?:tCO2e|metric tons?)',
                r'[Vv]alue chain emissions[^0-9]*?([0-9,]+\.?\d*)\s*(?:tCO2e|metric tons?)',
                r'[Oo]ther indirect emissions[^0-9]*?([0-9,]+\.?\d*)\s*(?:tCO2e|metric tons?)',
            ],
            'total_emissions': [
                r'[Tt]otal emissions[^0-9]*?([0-9,]+\.?\d*)\s*(?:tCO2e|metric tons?)',
                r'[Tt]otal GHG[^0-9]*?([0-9,]+\.?\d*)\s*(?:tCO2e|metric tons?)',
                r'[Gg]ross emissions[^0-9]*?([0-9,]+\.?\d*)\s*(?:tCO2e|metric tons?)',
            ],
            'renewable_pct': [
                r'[Rr]enewable[^0-9]*?([0-9,]+\.?\d*)\s*%',
                r'([0-9,]+\.?\d*)%\s*renewable',
                r'[Rr]enewable energy[^0-9]*?([0-9,]+\.?\d*)',
            ],
            'energy_consumption': [
                r'[Ee]nergy consumption[^0-9]*?([0-9,]+\.?\d*)\s*(?:MWh|GWh|TWh)',
                r'Total energy[^0-9]*?([0-9,]+\.?\d*)\s*(?:MWh|GWh|TWh)',
            ],
        }
        
        # Year patterns
        self.year_patterns = [
            r'[Rr]eporting year[^0-9]*?(20\d{2})',
            r'[Ff]iscal year[^0-9]*?(20\d{2})',
            r'FY\s*(20\d{2})',
            r'Year ended[^0-9]*?(20\d{2})',
            r'Annual Report[^0-9]*?(20\d{2})',
            r'(?:January|February|March|April|May|June|July|August|September|October|November|December)[^0-9]*?20\d{2}',
        ]
        
        # Methodology patterns
        self.methodology_patterns = [
            r'GHG Protocol',
            r'ISO 14064',
            r'[Gg]reenhouse [Gg]as [Pp]rotocol',
            r'[Ww]orld [Rr]esources [Ii]nstitute',
            r'WRI/WBCSD',
        ]
        
        # Verification patterns
        self.verification_patterns = [
            r'third-party (?:verified|assurance|audit)',
            r'independent (?:verification|assurance)',
            r'assurance (?:statement|opinion)',
            r'limited assurance',
            r'reasonable assurance',
        ]
    
    def extract(self, pdf_path: Path, report_year: Optional[int] = None) -> ExtractedEmissionsData:
        """Extract emissions data from PDF using rules"""
        data = ExtractedEmissionsData(extraction_method='rule_based')
        
        try:
            # Open PDF
            doc = fitz.open(str(pdf_path))
            data.reporting_year = report_year
            
            # Extract text from all pages
            full_text = ""
            for page_num in range(len(doc)):
                if page_num >= settings.extraction.max_pages_per_pdf:
                    logger.warning(f"PDF exceeds max pages limit: {pdf_path}")
                    break
                
                page = doc[page_num]
                full_text += page.get_text() + "\n"
            
            doc.close()
            
            # Extract emissions data
            data.scope_1_absolute = self._extract_scope_1(full_text)
            data.scope_2_location_based = self._extract_scope_2_location(full_text)
            data.scope_2_market_based = self._extract_scope_2_market(full_text)
            data.scope_3_total = self._extract_scope_3(full_text)
            data.total_emissions = self._extract_total_emissions(full_text)
            data.renewable_energy_pct = self._extract_renewable_pct(full_text)
            data.energy_consumption_mwh = self._extract_energy_consumption(full_text)
            
            # Extract metadata
            data.reporting_year = self._extract_year(full_text) or report_year
            data.scope_1_methodology = self._extract_methodology(full_text, 'scope_1')
            data.scope_2_methodology = self._extract_methodology(full_text, 'scope_2')
            data.scope_3_methodology = self._extract_methodology(full_text, 'scope_3')
            data.third_party_verified = self._extract_verification(full_text)
            
            # Extract Scope 3 categories if available
            data.scope_3_categories = self._extract_scope3_categories(full_text)
            
            # Calculate confidence score
            data.confidence_score = self._calculate_confidence(data, full_text)
            
            # Store raw snippets for audit
            data.raw_snippets = self._extract_relevant_snippets(full_text)
            
            logger.info(f"Rule-based extraction complete. Confidence: {data.confidence_score:.2f}")
            
        except Exception as e:
            logger.error(f"Rule-based extraction failed: {e}")
            data.confidence_score = 0.0
        
        return data
    
    def _parse_number(self, text: str) -> Optional[float]:
        """Parse number from text, handling various formats"""
        if not text:
            return None
        
        # Remove commas and convert to float
        cleaned = text.replace(',', '').replace(' ', '')
        
        # Handle millions/billions
        multiplier = 1
        if 'million' in cleaned.lower() or 'mn' in cleaned.lower():
            multiplier = 1_000_000
            cleaned = re.sub(r'(million|mn)', '', cleaned, flags=re.IGNORECASE)
        elif 'billion' in cleaned.lower() or 'bn' in cleaned.lower():
            multiplier = 1_000_000_000
            cleaned = re.sub(r'(billion|bn)', '', cleaned, flags=re.IGNORECASE)
        
        try:
            return float(cleaned) * multiplier
        except ValueError:
            return None
    
    def _extract_with_patterns(self, text: str, patterns: List[str]) -> Optional[float]:
        """Extract number using multiple regex patterns"""
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            if matches:
                # Get the first match, handle groups
                match = matches[0]
                if isinstance(match, tuple):
                    match = match[0]  # First group
                
                # Parse the number
                value = self._parse_number(match)
                if value is not None:
                    return value
        
        return None
    
    def _extract_scope_1(self, text: str) -> Optional[float]:
        """Extract Scope 1 emissions"""
        return self._extract_with_patterns(text, self.emission_patterns['scope_1'])
    
    def _extract_scope_2_location(self, text: str) -> Optional[float]:
        """Extract Scope 2 location-based emissions"""
        return self._extract_with_patterns(text, self.emission_patterns['scope_2_location'])
    
    def _extract_scope_2_market(self, text: str) -> Optional[float]:
        """Extract Scope 2 market-based emissions"""
        return self._extract_with_patterns(text, self.emission_patterns['scope_2_market'])
    
    def _extract_scope_3(self, text: str) -> Optional[float]:
        """Extract Scope 3 emissions"""
        return self._extract_with_patterns(text, self.emission_patterns['scope_3'])
    
    def _extract_total_emissions(self, text: str) -> Optional[float]:
        """Extract total emissions"""
        return self._extract_with_patterns(text, self.emission_patterns['total_emissions'])
    
    def _extract_renewable_pct(self, text: str) -> Optional[float]:
        """Extract renewable energy percentage"""
        return self._extract_with_patterns(text, self.emission_patterns['renewable_pct'])
    
    def _extract_energy_consumption(self, text: str) -> Optional[float]:
        """Extract energy consumption"""
        value = self._extract_with_patterns(text, self.emission_patterns['energy_consumption'])
        if value:
            # Normalize to MWh if needed
            if 'GWh' in text.upper():
                value *= 1000
            elif 'TWh' in text.upper():
                value *= 1_000_000
        return value
    
    def _extract_year(self, text: str) -> Optional[int]:
        """Extract reporting year"""
        for pattern in self.year_patterns:
            match = re.search(pattern, text)
            if match:
                year = int(match.group(1))
                if 2010 <= year <= 2030:
                    return year
        return None
    
    def _extract_methodology(self, text: str, scope: str) -> Optional[str]:
        """Extract methodology information"""
        # Look for methodology mentions near scope mentions
        scope_section = re.search(
            rf'[Ss]cope\s*{scope[-1]}[^.]*?{{1000}}', 
            text, 
            re.IGNORECASE | re.DOTALL
        )
        
        if scope_section:
            section_text = scope_section.group(0)
            for pattern in self.methodology_patterns:
                if re.search(pattern, section_text, re.IGNORECASE):
                    return pattern
        
        # Check entire text
        for pattern in self.methodology_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return pattern
        
        return None
    
    def _extract_verification(self, text: str) -> Optional[str]:
        """Extract verification status"""
        for pattern in self.verification_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return "Yes"
        return None
    
    def _extract_scope3_categories(self, text: str) -> Dict[str, float]:
        """Extract detailed Scope 3 categories if available"""
        categories = {}
        
        # Standard GHG Protocol categories
        category_patterns = {
            'purchased_goods': r'[Cc]ategory\s*1[^0-9]*?([0-9,]+\.?\d*)',
            'capital_goods': r'[Cc]ategory\s*2[^0-9]*?([0-9,]+\.?\d*)',
            'fuel_energy': r'[Cc]ategory\s*3[^0-9]*?([0-9,]+\.?\d*)',
            'transport': r'[Cc]ategory\s*4[^0-9]*?([0-9,]+\.?\d*)',
            'waste': r'[Cc]ategory\s*5[^0-9]*?([0-9,]+\.?\d*)',
            'business_travel': r'[Cc]ategory\s*6[^0-9]*?([0-9,]+\.?\d*)',
            'employee_commuting': r'[Cc]ategory\s*7[^0-9]*?([0-9,]+\.?\d*)',
        }
        
        for category, pattern in category_patterns.items():
            match = re.search(pattern, text)
            if match:
                value = self._parse_number(match.group(1))
                if value:
                    categories[category] = value
        
        return categories
    
    def _extract_relevant_snippets(self, text: str, max_length: int = 500) -> Dict[str, str]:
        """Extract relevant text snippets for each emission type"""
        snippets = {}
        
        # Find sections for each scope
        for scope in ['scope 1', 'scope 2', 'scope 3']:
            pattern = rf'([^.]*?{scope}[^.]{{0,200}})'
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                snippets[scope.replace(' ', '_')] = matches[0][:max_length]
        
        return snippets
    
    def _calculate_confidence(self, data: ExtractedEmissionsData, text: str) -> float:
        """Calculate confidence score for extraction"""
        scores = []
        
        # Score based on data completeness
        fields = [
            data.scope_1_absolute,
            data.scope_2_location_based,
            data.scope_3_total,
            data.total_emissions,
        ]
        filled = sum(1 for f in fields if f is not None)
        completeness_score = filled / len(fields)
        scores.append(completeness_score)
        
        # Score based on text mentions
        text_lower = text.lower()
        keyword_score = 0
        keywords = ['ghg', 'emissions', 'tco2e', 'carbon', 'scope 1', 'scope 2', 'scope 3']
        for kw in keywords:
            if kw in text_lower:
                keyword_score += 1
        keyword_score /= len(keywords)
        scores.append(keyword_score)
        
        # Score based on methodology mention
        methodology_score = 1.0 if data.scope_1_methodology or data.scope_2_methodology else 0.5
        scores.append(methodology_score)
        
        # Average scores
        return sum(scores) / len(scores)


class HybridExtractor:
    """Hybrid extraction combining rule-based and LLM approaches"""
    
    def __init__(self, llm_extractor=None):
        self.rule_extractor = RuleBasedExtractor()
        self.llm_extractor = llm_extractor
    
    def extract(self, pdf_path: Path, report_year: Optional[int] = None) -> ExtractedEmissionsData:
        """Extract data using hybrid approach"""
        logger.info(f"Starting hybrid extraction for: {pdf_path}")
        
        # Step 1: Rule-based extraction
        data = self.rule_extractor.extract(pdf_path, report_year)
        
        # Step 2: Check if LLM fallback is needed
        if settings.extraction.use_llm_fallback and \
           data.confidence_score < settings.extraction.llm_trigger_threshold:
            logger.info(f"Rule-based confidence ({data.confidence_score:.2f}) below threshold, triggering LLM")
            
            if self.llm_extractor:
                try:
                    llm_data = self.llm_extractor.extract(pdf_path, report_year)
                    
                    # Merge LLM data with rule-based (LLM fills gaps)
                    data = self._merge_extractions(data, llm_data)
                    data.extraction_method = 'hybrid'
                    
                except Exception as e:
                    logger.error(f"LLM extraction failed: {e}")
                    data.extraction_method = 'rule_based (llm_failed)'
            else:
                logger.warning("LLM extractor not configured")
        
        return data
    
    def _merge_extractions(self, rule_data: ExtractedEmissionsData,
                          llm_data: ExtractedEmissionsData) -> ExtractedEmissionsData:
        """Merge rule-based and LLM extractions, preferring higher confidence values"""
        merged = ExtractedEmissionsData(extraction_method='hybrid')
        
        # Prefer LLM for unstructured fields, rule-based for structured tables
        fields = [
            'scope_1_absolute', 'scope_2_location_based', 'scope_2_market_based',
            'scope_3_total', 'total_emissions', 'renewable_energy_pct',
            'energy_consumption_mwh', 'reporting_year', 'baseline_year'
        ]
        
        for field in fields:
            rule_val = getattr(rule_data, field)
            llm_val = getattr(llm_data, field)
            
            # Use rule-based if available and seems reasonable
            if rule_val is not None:
                # Validate against LLM if both present
                if llm_val is not None:
                    # Check if values are within 20% of each other
                    if rule_val > 0 and abs(rule_val - llm_val) / rule_val < 0.2:
                        setattr(merged, field, rule_val)  # Prefer rule-based
                    else:
                        setattr(merged, field, llm_val)  # Use LLM if rule seems off
                else:
                    setattr(merged, field, rule_val)
            else:
                setattr(merged, field, llm_val)
        
        # Merge dict fields
        merged.scope_3_categories = {**rule_data.scope_3_categories, **llm_data.scope_3_categories}
        merged.emission_targets = {**rule_data.emission_targets, **llm_data.emission_targets}
        merged.raw_snippets = {**rule_data.raw_snippets, **llm_data.raw_snippets}
        
        # Take highest confidence methodology
        merged.scope_1_methodology = rule_data.scope_1_methodology or llm_data.scope_1_methodology
        merged.scope_2_methodology = rule_data.scope_2_methodology or llm_data.scope_2_methodology
        merged.scope_3_methodology = rule_data.scope_3_methodology or llm_data.scope_3_methodology
        
        # Calculate blended confidence
        merged.confidence_score = max(rule_data.confidence_score, llm_data.confidence_score)
        
        return merged
