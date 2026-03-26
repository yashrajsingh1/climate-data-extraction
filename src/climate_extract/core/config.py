"""
Climate Data Extraction System - Configuration Module
Centralized configuration management using Pydantic Settings
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
from pathlib import Path


class DatabaseConfig(BaseSettings):
    """Database configuration settings"""
    url: str = "sqlite:///./data/climate_data.db"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    
    class Config:
        env_prefix = "DB_"


class LLMConfig(BaseSettings):
    """LLM API configuration for fallback extraction"""
    provider: str = "openai"  # openai, anthropic, or local
    api_key: Optional[str] = None
    model: str = "gpt-4"
    temperature: float = 0.1
    max_tokens: int = 4000
    timeout: int = 60
    
    class Config:
        env_prefix = "LLM_"


class ExtractionConfig(BaseSettings):
    """PDF extraction configuration"""
    # Rule-based extraction thresholds
    min_confidence_score: float = 0.7
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    # LLM fallback triggers
    use_llm_fallback: bool = True
    llm_trigger_threshold: float = 0.5  # Trigger LLM if rule-based confidence < 0.5
    
    # Processing limits
    max_pdf_size_mb: int = 50
    max_pages_per_pdf: int = 500
    
    class Config:
        env_prefix = "EXTRACT_"


class DiscoveryConfig(BaseSettings):
    """Report discovery configuration"""
    # Search settings
    search_engines: List[str] = ["google", "bing"]
    max_results_per_source: int = 10
    request_timeout: int = 30
    
    # Rate limiting
    requests_per_minute: int = 30
    retry_attempts: int = 3
    retry_delay: int = 2
    
    # ESG portals to check
    esg_portals: List[str] = [
        "https://www.sustainalytics.com",
        "https://www.msci.com",
        "https://www.refinitiv.com",
        "https://www.cdp.net",
    ]
    
    class Config:
        env_prefix = "DISCOVERY_"


class StorageConfig(BaseSettings):
    """File storage configuration"""
    raw_data_path: Path = Path("./data/raw")
    processed_data_path: Path = Path("./data/processed")
    reports_path: Path = Path("./data/reports")
    
    # Retention
    keep_raw_pdfs: bool = True
    keep_processed_json: bool = True
    
    class Config:
        env_prefix = "STORAGE_"


class Settings(BaseSettings):
    """Main application settings"""
    app_name: str = "Climate Data Extraction System"
    version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # Sub-configs
    db: DatabaseConfig = DatabaseConfig()
    llm: LLMConfig = LLMConfig()
    extraction: ExtractionConfig = ExtractionConfig()
    discovery: DiscoveryConfig = DiscoveryConfig()
    storage: StorageConfig = StorageConfig()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
