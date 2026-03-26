"""
LLM-based Text Extraction Module
Uses OpenAI API for intelligent extraction of emissions data from text
"""

import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
import openai

logger = logging.getLogger(__name__)


@dataclass
class EmissionsExtraction:
    """Structured emissions data extracted from text"""
    scope_1: Optional[float] = None
    scope_2: Optional[float] = None
    scope_3: Optional[float] = None
    total_emissions: Optional[float] = None
    unit: str = "tCO2e"
    year: Optional[int] = None
    confidence: float = 0.0
    raw_text: str = ""


class LLMExtractor:
    """Extract emissions data using OpenAI LLM"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        """
        Initialize LLM extractor
        
        Args:
            api_key: OpenAI API key (if None, will try to use environment)
            model: Model to use (gpt-4, gpt-3.5-turbo)
        """
        if api_key:
            openai.api_key = api_key
        self.model = model
        self.client = openai.OpenAI() if api_key else None
    
    def extract_emissions(self, text: str) -> EmissionsExtraction:
        """
        Extract emissions data from text using LLM
        
        Args:
            text: Text to analyze
            
        Returns:
            EmissionsExtraction with extracted data
        """
        if not self.client:
            logger.warning("LLM client not initialized")
            return EmissionsExtraction(confidence=0.0)
        
        try:
            prompt = self._build_extraction_prompt(text)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a climate data extraction specialist. Extract emissions data accurately."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            extraction = EmissionsExtraction(
                scope_1=self._parse_number(result.get('scope_1')),
                scope_2=self._parse_number(result.get('scope_2')),
                scope_3=self._parse_number(result.get('scope_3')),
                total_emissions=self._parse_number(result.get('total_emissions')),
                unit=result.get('unit', 'tCO2e'),
                year=result.get('year'),
                confidence=result.get('confidence', 0.5),
                raw_text=text[:500]  # Store preview
            )
            
            logger.info(f"LLM extraction complete: Scope 1={extraction.scope_1}, Scope 2={extraction.scope_2}")
            return extraction
            
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return EmissionsExtraction(confidence=0.0)
    
    def _build_extraction_prompt(self, text: str) -> str:
        """Build the extraction prompt"""
        return f"""Analyze the following text from a sustainability report and extract emissions data.

Text to analyze:
{text[:8000]}  # Limit text length

Extract the following information and return as JSON:
- scope_1: Direct emissions (fuel, vehicles) - number only
- scope_2: Indirect emissions (electricity) - number only  
- scope_3: Value chain emissions - number only
- total_emissions: Total if explicitly stated - number only
- unit: Unit of measurement (e.g., "tCO2e", "MtCO2e")
- year: Reporting year
- confidence: Your confidence 0-1

Return format:
{{
    "scope_1": number or null,
    "scope_2": number or null,
    "scope_3": number or null,
    "total_emissions": number or null,
    "unit": "string",
    "year": number or null,
    "confidence": number
}}"""
    
    def _parse_number(self, value: Any) -> Optional[float]:
        """Parse a number from various formats"""
        if value is None:
            return None
        try:
            if isinstance(value, (int, float)):
                return float(value)
            # Remove commas and units
            cleaned = str(value).replace(',', '').replace(' ', '')
            return float(cleaned)
        except:
            return None


class HybridExtractor:
    """Combines rule-based and LLM extraction"""
    
    def __init__(self, llm_extractor: Optional[LLMExtractor] = None):
        self.llm = llm_extractor
    
    def extract(self, text: str, use_llm: bool = True) -> EmissionsExtraction:
        """
        Extract emissions using hybrid approach
        
        First tries rule-based extraction, falls back to LLM if confidence is low
        """
        # Rule-based extraction first
        rule_result = self._rule_based_extract(text)
        
        # If confidence is low and LLM is available, try LLM
        if rule_result.confidence < 0.7 and use_llm and self.llm:
            llm_result = self.llm.extract_emissions(text)
            
            # Use LLM result if higher confidence
            if llm_result.confidence > rule_result.confidence:
                return llm_result
        
        return rule_result
    
    def _rule_based_extract(self, text: str) -> EmissionsExtraction:
        """Simple rule-based extraction using regex patterns"""
        import re
        
        result = EmissionsExtraction()
        
        # Patterns for emissions data
        patterns = {
            'scope_1': [
                r'Scope\s*1.*?([\d,\.]+)\s*(?:tCO2e|tonnes?)?',
                r'direct emissions.*?([\d,\.]+)',
            ],
            'scope_2': [
                r'Scope\s*2.*?([\d,\.]+)\s*(?:tCO2e|tonnes?)?',
                r'indirect emissions.*?([\d,\.]+)',
            ],
            'scope_3': [
                r'Scope\s*3.*?([\d,\.]+)\s*(?:tCO2e|tonnes?)?',
                r'value chain.*?([\d,\.]+)',
            ],
            'year': [
                r'reporting year.*?20(\d{2})',
                r'fiscal year.*?20(\d{2})',
            ]
        }
        
        for field, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1).replace(',', '')
                    try:
                        num = float(value)
                        if field == 'year':
                            result.year = int(num) + 2000
                        else:
                            setattr(result, field, num)
                        result.confidence += 0.2
                    except:
                        pass
                    break
        
        result.confidence = min(result.confidence, 1.0)
        return result
