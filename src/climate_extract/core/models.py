"""
Climate Data Extraction System - Data Models
SQLAlchemy ORM models for database storage + Pydantic models for validation
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, 
    Text, JSON, ForeignKey, Index, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.ext.declarative import declared_attr
from pydantic import BaseModel, Field, field_validator

from climate_extract.core.config import settings


# SQLAlchemy Base
Base = declarative_base()


class Company(Base):
    """Company information table"""
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    ticker = Column(String(20), nullable=True, index=True)
    industry = Column(String(100), nullable=True)
    website = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    reports = relationship("SustainabilityReport", back_populates="company")
    emissions = relationship("EmissionsData", back_populates="company")
    
    __table_args__ = (
        Index('idx_company_name_ticker', 'name', 'ticker'),
    )


class SustainabilityReport(Base):
    """Climate/sustainability reports metadata"""
    __tablename__ = "sustainability_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    report_year = Column(Integer, nullable=False, index=True)
    report_type = Column(String(50), nullable=False)  # annual, sustainability, esg, csr
    title = Column(String(500), nullable=True)
    source_url = Column(String(1000), nullable=False)
    local_path = Column(String(500), nullable=True)
    file_size_mb = Column(Float, nullable=True)
    page_count = Column(Integer, nullable=True)
    
    # Extraction metadata
    extraction_method = Column(String(50), nullable=True)  # rule_based, llm, hybrid
    extraction_confidence = Column(Float, nullable=True)
    extraction_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    
    # Raw extracted content
    raw_content = Column(Text, nullable=True)
    extracted_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="reports")
    emissions_data = relationship("EmissionsData", back_populates="report")
    
    __table_args__ = (
        Index('idx_report_company_year', 'company_id', 'report_year'),
        Index('idx_report_status', 'extraction_status'),
    )


class EmissionsData(Base):
    """Structured emissions data extracted from reports"""
    __tablename__ = "emissions_data"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    report_id = Column(Integer, ForeignKey("sustainability_reports.id"), nullable=True)
    
    # Year and period
    reporting_year = Column(Integer, nullable=False, index=True)
    baseline_year = Column(Integer, nullable=True)
    
    # Scope 1 emissions (tCO2e)
    scope_1_absolute = Column(Float, nullable=True)
    scope_1_intensity = Column(Float, nullable=True)  # per revenue/unit
    scope_1_methodology = Column(String(255), nullable=True)
    
    # Scope 2 emissions (tCO2e)
    scope_2_location_based = Column(Float, nullable=True)
    scope_2_market_based = Column(Float, nullable=True)
    scope_2_intensity = Column(Float, nullable=True)
    scope_2_methodology = Column(String(255), nullable=True)
    
    # Scope 3 emissions (tCO2e)
    scope_3_total = Column(Float, nullable=True)
    scope_3_categories = Column(JSON, nullable=True)  # Dict of category -> value
    scope_3_methodology = Column(String(255), nullable=True)
    
    # Totals
    total_emissions = Column(Float, nullable=True)
    net_emissions = Column(Float, nullable=True)  # after offsets
    
    # Targets and commitments
    emission_targets = Column(JSON, nullable=True)  # Dict of target info
    reduction_targets = Column(JSON, nullable=True)
    
    # Additional metrics
    renewable_energy_pct = Column(Float, nullable=True)
    energy_consumption_mwh = Column(Float, nullable=True)
    carbon_intensity = Column(Float, nullable=True)
    
    # Verification
    third_party_verified = Column(String(100), nullable=True)
    verification_standard = Column(String(100), nullable=True)
    
    # Metadata
    extracted_at = Column(DateTime, default=datetime.utcnow)
    extraction_method = Column(String(50), nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    # Raw snippets for audit
    raw_snippets = Column(JSON, nullable=True)
    
    # Relationships
    company = relationship("Company", back_populates="emissions")
    report = relationship("SustainabilityReport", back_populates="emissions_data")
    
    __table_args__ = (
        Index('idx_emissions_company_year', 'company_id', 'reporting_year'),
        Index('idx_emissions_scope1', 'scope_1_absolute'),
        Index('idx_emissions_scope2', 'scope_2_location_based'),
        Index('idx_emissions_scope3', 'scope_3_total'),
    )


class ProcessingJob(Base):
    """Track ETL and processing jobs"""
    __tablename__ = "processing_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_type = Column(String(50), nullable=False)  # discovery, extraction, etl
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    
    # Job parameters
    company_name = Column(String(255), nullable=True)
    parameters = Column(JSON, nullable=True)
    
    # Progress tracking
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    
    # Results
    result_summary = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Models for API/Validation

class CompanyCreate(BaseModel):
    """Model for creating a new company"""
    name: str = Field(..., min_length=1, max_length=255)
    ticker: Optional[str] = Field(None, max_length=20)
    industry: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=500)


class CompanyResponse(CompanyCreate):
    """Model for company response"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class EmissionsDataCreate(BaseModel):
    """Model for creating emissions data"""
    company_id: int
    report_id: Optional[int] = None
    reporting_year: int = Field(..., ge=1990, le=2100)
    
    scope_1_absolute: Optional[float] = Field(None, ge=0)
    scope_2_location_based: Optional[float] = Field(None, ge=0)
    scope_2_market_based: Optional[float] = Field(None, ge=0)
    scope_3_total: Optional[float] = Field(None, ge=0)
    scope_3_categories: Optional[Dict[str, float]] = None
    
    total_emissions: Optional[float] = None
    renewable_energy_pct: Optional[float] = Field(None, ge=0, le=100)
    energy_consumption_mwh: Optional[float] = Field(None, ge=0)
    
    emission_targets: Optional[Dict[str, Any]] = None
    third_party_verified: Optional[str] = None
    
    @field_validator('total_emissions')
    @classmethod
    def validate_total(cls, v, values):
        """Validate total emissions is greater than sum of scopes"""
        if v is not None:
            scope_1 = values.data.get('scope_1_absolute', 0) or 0
            scope_2 = values.data.get('scope_2_location_based', 0) or 0
            scope_3 = values.data.get('scope_3_total', 0) or 0
            calculated_total = scope_1 + scope_2 + scope_3
            
            if calculated_total > 0 and v < calculated_total * 0.5:
                raise ValueError("Total emissions seems too low compared to scope sum")
        return v


class EmissionsDataResponse(EmissionsDataCreate):
    """Model for emissions data response"""
    id: int
    extracted_at: datetime
    extraction_method: Optional[str]
    confidence_score: Optional[float]
    
    class Config:
        from_attributes = True


class ReportCreate(BaseModel):
    """Model for creating a report record"""
    company_id: int
    report_year: int
    report_type: str = Field(..., pattern="^(annual|sustainability|esg|csr)$")
    title: Optional[str] = None
    source_url: str
    local_path: Optional[str] = None


class ReportResponse(ReportCreate):
    """Model for report response"""
    id: int
    extraction_status: str
    extraction_confidence: Optional[float]
    extracted_at: datetime
    
    class Config:
        from_attributes = True


# Database engine and session factory
def get_engine():
    """Create database engine"""
    return create_engine(
        settings.db.url,
        echo=settings.db.echo,
        pool_size=settings.db.pool_size,
        max_overflow=settings.db.max_overflow
    )


def get_session_factory():
    """Get configured session factory"""
    engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables"""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
