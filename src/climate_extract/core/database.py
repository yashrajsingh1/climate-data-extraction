"""
Climate Data Extraction System - Database Layer
Repository pattern for data access
"""

from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from climate_extract.core.models import (
    Base, get_session_factory, Company, SustainabilityReport,
    EmissionsData, ProcessingJob
)


class DatabaseRepository:
    """Generic repository for database operations"""
    
    def __init__(self, session: Session = None):
        self.session = session
        self.SessionLocal = get_session_factory()
    
    @contextmanager
    def get_db(self):
        """Context manager for database sessions"""
        db = self.SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    
    # Company operations
    def get_or_create_company(self, name: str, **kwargs) -> Company:
        """Get existing company or create new one"""
        with self.get_db() as db:
            company = db.query(Company).filter(
                func.lower(Company.name) == func.lower(name)
            ).first()
            
            if not company:
                company = Company(
                    name=name,
                    ticker=kwargs.get('ticker'),
                    industry=kwargs.get('industry'),
                    website=kwargs.get('website')
                )
                db.add(company)
                db.flush()  # Get ID without committing
                db.refresh(company)
            
            # Expunge from session so it can be used after session closes
            db.expunge(company)
            return company
    
    def get_company_by_name(self, name: str) -> Optional[Company]:
        """Find company by name (case insensitive)"""
        with self.get_db() as db:
            return db.query(Company).filter(
                func.lower(Company.name) == func.lower(name)
            ).first()
    
    def get_company_by_ticker(self, ticker: str) -> Optional[Company]:
        """Find company by stock ticker"""
        with self.get_db() as db:
            return db.query(Company).filter(
                func.upper(Company.ticker) == func.upper(ticker)
            ).first()
    
    def list_companies(self, limit: int = 100, offset: int = 0) -> List[Company]:
        """List all companies with pagination"""
        with self.get_db() as db:
            return db.query(Company).offset(offset).limit(limit).all()
    
    # Report operations
    def create_report(self, company_id: int, report_year: int,
                     report_type: str, source_url: str, **kwargs) -> SustainabilityReport:
        """Create a new report record"""
        with self.get_db() as db:
            report = SustainabilityReport(
                company_id=company_id,
                report_year=report_year,
                report_type=report_type,
                source_url=source_url,
                title=kwargs.get('title'),
                local_path=kwargs.get('local_path'),
                file_size_mb=kwargs.get('file_size_mb'),
                page_count=kwargs.get('page_count'),
                extraction_status='pending'
            )
            db.add(report)
            db.flush()
            db.refresh(report)
            db.expunge(report)
            return report
    
    def get_report_by_url(self, url: str) -> Optional[SustainabilityReport]:
        """Check if report already exists by URL"""
        with self.get_db() as db:
            return db.query(SustainabilityReport).filter(
                SustainabilityReport.source_url == url
            ).first()
    
    def get_company_reports(self, company_id: int, 
                           year: Optional[int] = None) -> List[SustainabilityReport]:
        """Get all reports for a company, optionally filtered by year"""
        with self.get_db() as db:
            query = db.query(SustainabilityReport).filter(
                SustainabilityReport.company_id == company_id
            )
            if year:
                query = query.filter(SustainabilityReport.report_year == year)
            return query.order_by(SustainabilityReport.report_year.desc()).all()
    
    def update_report_extraction(self, report_id: int, 
                                  status: str, 
                                  method: Optional[str] = None,
                                  confidence: Optional[float] = None,
                                  raw_content: Optional[str] = None):
        """Update report extraction status and metadata"""
        with self.get_db() as db:
            report = db.query(SustainabilityReport).get(report_id)
            if report:
                report.extraction_status = status
                if method:
                    report.extraction_method = method
                if confidence is not None:
                    report.extraction_confidence = confidence
                if raw_content:
                    report.raw_content = raw_content
                report.extracted_at = datetime.utcnow()
    
    # Emissions data operations
    def create_emissions_data(self, **kwargs) -> EmissionsData:
        """Create emissions data record"""
        with self.get_db() as db:
            emissions = EmissionsData(**kwargs)
            db.add(emissions)
            db.flush()
            db.refresh(emissions)
            return emissions
    
    def get_emissions_by_company_year(self, company_id: int, 
                                      year: int) -> Optional[EmissionsData]:
        """Get emissions data for company and year"""
        with self.get_db() as db:
            return db.query(EmissionsData).filter(
                and_(
                    EmissionsData.company_id == company_id,
                    EmissionsData.reporting_year == year
                )
            ).first()
    
    def get_company_emissions_history(self, company_id: int) -> List[EmissionsData]:
        """Get all historical emissions data for a company"""
        with self.get_db() as db:
            return db.query(EmissionsData).filter(
                EmissionsData.company_id == company_id
            ).order_by(EmissionsData.reporting_year.desc()).all()
    
    def upsert_emissions_data(self, company_id: int, reporting_year: int, 
                             **data) -> EmissionsData:
        """Update existing or create new emissions data"""
        with self.get_db() as db:
            existing = self.get_emissions_by_company_year(company_id, reporting_year)
            
            if existing:
                # Update existing record
                for key, value in data.items():
                    if hasattr(existing, key) and value is not None:
                        setattr(existing, key, value)
                existing.extracted_at = datetime.utcnow()
                db.flush()
                db.refresh(existing)
                return existing
            else:
                # Create new record
                return self.create_emissions_data(
                    company_id=company_id,
                    reporting_year=reporting_year,
                    **data
                )
    
    # Job tracking operations
    def create_job(self, job_type: str, company_name: Optional[str] = None,
                  parameters: Optional[Dict] = None) -> ProcessingJob:
        """Create a new processing job"""
        with self.get_db() as db:
            job = ProcessingJob(
                job_type=job_type,
                company_name=company_name,
                parameters=parameters or {}
            )
            db.add(job)
            db.flush()
            db.refresh(job)
            return job
    
    def update_job_status(self, job_id: int, status: str,
                         progress: Optional[Dict] = None,
                         result: Optional[Dict] = None,
                         error: Optional[str] = None):
        """Update job status and progress"""
        with self.get_db() as db:
            job = db.query(ProcessingJob).get(job_id)
            if job:
                job.status = status
                
                if progress:
                    job.total_items = progress.get('total', job.total_items)
                    job.processed_items = progress.get('processed', job.processed_items)
                    job.failed_items = progress.get('failed', job.failed_items)
                
                if result:
                    job.result_summary = result
                
                if error:
                    job.error_message = error
                
                if status == 'running' and not job.started_at:
                    job.started_at = datetime.utcnow()
                
                if status in ['completed', 'failed']:
                    job.completed_at = datetime.utcnow()
    
    # Analytics queries
    def get_emissions_trends(self, company_id: int) -> List[Dict]:
        """Get year-over-year emissions trends for a company"""
        with self.get_db() as db:
            results = db.query(
                EmissionsData.reporting_year,
                EmissionsData.scope_1_absolute,
                EmissionsData.scope_2_location_based,
                EmissionsData.scope_3_total,
                EmissionsData.total_emissions,
                EmissionsData.renewable_energy_pct
            ).filter(
                EmissionsData.company_id == company_id
            ).order_by(EmissionsData.reporting_year).all()
            
            return [
                {
                    'year': r.reporting_year,
                    'scope_1': r.scope_1_absolute,
                    'scope_2': r.scope_2_location_based,
                    'scope_3': r.scope_3_total,
                    'total': r.total_emissions,
                    'renewable_pct': r.renewable_energy_pct
                }
                for r in results
            ]
    
    def get_companies_with_data(self, min_year: Optional[int] = None) -> List[Company]:
        """Get companies that have emissions data"""
        with self.get_db() as db:
            query = db.query(Company).join(
                EmissionsData, Company.id == EmissionsData.company_id
            ).distinct()
            
            if min_year:
                query = query.filter(EmissionsData.reporting_year >= min_year)
            
            return query.all()
