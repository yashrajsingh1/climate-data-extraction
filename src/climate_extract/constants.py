"""
Climate Data Extraction System - Constants and Patterns
Centralized configuration for regex patterns, keywords, and constants
"""

# Emissions Data Patterns
SCOPE1_PATTERNS = [
    r'scope\s*1(?:\s*emissions?)?[:\s]+([0-9,\.]+)\s*(?:mt)?co2e',
    r'scope\s*1[:\s]+([0-9,\.]+)\s*(?:metric\s*)?tonnes?',
    r'direct\s*(?:greenhouse\s*gas\s*)?emissions?[:\s]+([0-9,\.]+)',
    r'scope\s*1\s*ghg[:\s]+([0-9,\.]+)',
]

SCOPE2_PATTERNS = [
    r'scope\s*2(?:\s*emissions?)?[:\s]+([0-9,\.]+)\s*(?:mt)?co2e',
    r'scope\s*2[:\s]+([0-9,\.]+)\s*(?:metric\s*)?tonnes?',
    r'indirect\s*(?:greenhouse\s*gas\s*)?emissions?[:\s]+([0-9,\.]+)',
    r'scope\s*2\s*ghg[:\s]+([0-9,\.]+)',
    r'electricity\s*(?:indirect\s*)?emissions?[:\s]+([0-9,\.]+)',
]

SCOPE3_PATTERNS = [
    r'scope\s*3(?:\s*emissions?)?[:\s]+([0-9,\.]+)\s*(?:mt)?co2e',
    r'scope\s*3[:\s]+([0-9,\.]+)\s*(?:metric\s*)?tonnes?',
    r'value\s*chain\s*(?:greenhouse\s*gas\s*)?emissions?[:\s]+([0-9,\.]+)',
    r'scope\s*3\s*ghg[:\s]+([0-9,\.]+)',
]

YEAR_PATTERNS = [
    r'(?:fiscal\s*|reporting\s*)?year\s*(?:ended?\s*)?(?:on\s*)?(\d{4})',
    r'(\d{4})\s*(?:fiscal|reporting|annual|sustainability)\s*(?:report|year)',
    r'for\s*(?:the\s*)?(?:fiscal\s*)?year\s*(?:ended?\s*)?(?:december\s*31,?\s*)?(\d{4})',
]

TOTAL_EMISSIONS_PATTERNS = [
    r'total\s*(?:greenhouse\s*gas\s*)?(?:ghg\s*)?emissions?[:\s]+([0-9,\.]+)',
    r'total\s*co2e[:\s]+([0-9,\.]+)',
    r'aggregate\s*emissions?[:\s]+([0-9,\.]+)',
]

# Keyword patterns for report identification
SUSTAINABILITY_KEYWORDS = [
    'sustainability', 'esg', 'environmental', 'social', 'governance',
    'climate', 'carbon', 'emissions', 'green', 'renewable', 'responsible',
    'corporate responsibility', 'corporate social responsibility', 'csr',
    'impact', 'sdg', 'sustainable development', 'net zero', 'carbon neutral'
]

REPORT_TYPE_INDICATORS = {
    'sustainability': ['sustainability report', 'sustainability', 'sus'],
    'esg': ['esg report', 'esg disclosure', 'esg', 'environmental social'],
    'annual': ['annual report', 'fiscal year'],
    'csr': ['csr report', 'corporate social responsibility', 'csr'],
    'climate': ['climate report', 'climate action', 'climate disclosure'],
    'tcfd': ['tcfd', 'task force on climate-related'],
    'cdp': ['cdp disclosure', 'climate disclosure project'],
}

# URL patterns for discovery
DISCOVERY_PATHS = [
    '/sustainability',
    '/esg',
    '/csr',
    '/corporate-responsibility',
    '/climate',
    '/impact',
    '/investors',
    '/investor-relations',
    '/news',
    '/press-releases',
]

DISCOVERY_KEYWORDS = [
    'sustainability',
    'environmental',
    'esg',
    'carbon',
    'emissions',
    'climate',
    'responsible',
    'impact',
    'green',
]

# Unit conversions to metric tons CO2e
UNIT_CONVERSIONS = {
    'mtco2e': 1,
    'mtonnes': 1,
    'metric tonnes': 1,
    'metric tons': 1,
    'tco2e': 1,
    'tonnes co2e': 1,
    'tons co2e': 1,
    'kg co2e': 0.001,
    'kgco2e': 0.001,
    'g co2e': 0.000001,
    'gco2e': 0.000001,
}

# Common report types and their keywords
REPORT_TYPES = {
    'sustainability': ['sustainability', 'sus report'],
    'esg': ['esg', 'environmental social governance'],
    'annual': ['annual', 'fiscal year'],
    'climate': ['climate', 'climate action'],
    'csr': ['corporate social responsibility', 'csr'],
    'tcfd': ['task force climate-related', 'tcfd'],
    'cdp': ['climate disclosure', 'cdp'],
    'corporate': ['corporate responsibility', 'corporate report'],
}

# Confidence thresholds
CONFIDENCE_HIGH = 0.9
CONFIDENCE_MEDIUM = 0.7
CONFIDENCE_LOW = 0.5

# Request configuration
DEFAULT_TIMEOUT = 30
DOWNLOAD_TIMEOUT = 60
DEFAULT_RETRIES = 3
DEFAULT_RETRY_BACKOFF = 2

# File size limits (in MB)
MAX_PDF_SIZE = 100
MIN_PDF_SIZE = 0.1  # Skip very small files

# Rate limiting
DEFAULT_REQUESTS_PER_MINUTE = 10
DEFAULT_DELAY_BETWEEN_REQUESTS = 60 / DEFAULT_REQUESTS_PER_MINUTE
