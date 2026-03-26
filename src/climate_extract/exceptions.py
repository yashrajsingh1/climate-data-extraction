"""
Climate Data Extraction System - Custom Exceptions
Comprehensive error handling for all components
"""


class ClimateExtractionError(Exception):
    """Base exception for climate extraction system"""
    pass


class DiscoveryError(ClimateExtractionError):
    """Discovery layer errors"""
    pass


class URLDiscoveryError(DiscoveryError):
    """Failed to discover URLs"""
    pass


class WebsiteCrawlError(DiscoveryError):
    """Failed to crawl website"""
    pass


class GoogleSearchError(DiscoveryError):
    """Google search API error"""
    pass


class PDFDownloadError(ClimateExtractionError):
    """PDF download errors"""
    pass


class PDFDownloadTimeoutError(PDFDownloadError):
    """PDF download timeout"""
    pass


class PDFDownloadHTTPError(PDFDownloadError):
    """HTTP error during PDF download"""
    pass


class PDFDownloadInvalidError(PDFDownloadError):
    """Downloaded file is not a valid PDF"""
    pass


class ExtractionError(ClimateExtractionError):
    """Data extraction errors"""
    pass


class PDFParsingError(ExtractionError):
    """Failed to parse PDF text"""
    pass


class DataExtractionError(ExtractionError):
    """Failed to extract emissions data"""
    pass


class LLMExtractionError(ExtractionError):
    """LLM-based extraction failed"""
    pass


class RegexExtractionError(ExtractionError):
    """Regex-based extraction failed"""
    pass


class DatabaseError(ClimateExtractionError):
    """Database operation errors"""
    pass


class ConfigError(ClimateExtractionError):
    """Configuration errors"""
    pass


class MissingAPIKeyError(ConfigError):
    """Required API key is missing"""
    pass


class ValidationError(ClimateExtractionError):
    """Data validation errors"""
    pass


class InvalidCompanyNameError(ValidationError):
    """Invalid company name"""
    pass


class InvalidURLError(ValidationError):
    """Invalid URL"""
    pass


class InvalidEmissionsDataError(ValidationError):
    """Invalid emissions data"""
    pass


class RateLimitError(ClimateExtractionError):
    """Rate limit exceeded"""
    pass


class OrchestrationError(ClimateExtractionError):
    """Orchestrator pipeline errors"""
    pass
