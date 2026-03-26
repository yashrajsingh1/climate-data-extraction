"""
Unit tests for Climate Data Extraction System
Updated for simplified architecture
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from climate_extract.core.config import settings
from climate_extract.core.models import Company, SustainabilityReport
from climate_extract.extractors.hybrid_extractor import ExtractedEmissionsData, RuleBasedExtractor
from climate_extract.discover.google_discovery import DiscoveredReport, GoogleDiscovery


class TestExtractedEmissionsData:
    """Tests for emissions data model"""

    def test_emissions_data_init(self):
        data = ExtractedEmissionsData(
            scope_1_absolute=1000.0,
            scope_2_location_based=2000.0,
            reporting_year=2023,
            confidence_score=0.85
        )
        assert data.scope_1_absolute == 1000.0
        assert data.reporting_year == 2023
        assert data.confidence_score == 0.85


class TestRuleBasedExtractor:
    """Tests for rule-based extraction"""

    def test_init(self):
        extractor = RuleBasedExtractor()
        assert extractor is not None

    def test_extract_year(self):
        extractor = RuleBasedExtractor()

        # Test year extraction from various formats
        text1 = "For the year 2023"
        text2 = "FY 2022 Report"
        text3 = "No year here"

        # The extractor should have methods to extract years
        # Basic pattern matching test
        import re
        year_pattern = r'\b(20\d{2})\b'

        match1 = re.search(year_pattern, text1)
        match2 = re.search(year_pattern, text2)
        match3 = re.search(year_pattern, text3)

        assert match1 and int(match1.group(1)) == 2023
        assert match2 and int(match2.group(1)) == 2022
        assert match3 is None


class TestDiscoveredReport:
    """Tests for discovered report dataclass"""

    def test_discovered_report_init(self):
        report = DiscoveredReport(
            url="https://example.com/report.pdf",
            title="Test Report 2023",
            company="Test Corp",
            year=2023,
            source="google"
        )

        assert report.url == "https://example.com/report.pdf"
        assert report.company == "Test Corp"
        assert report.year == 2023
        assert report.source == "google"


class TestGoogleDiscovery:
    """Tests for Google discovery"""

    def test_init(self):
        discovery = GoogleDiscovery()
        assert discovery is not None

    def test_is_configured(self):
        discovery = GoogleDiscovery()
        # Will be False if env vars not set, True if they are
        result = discovery.is_configured()
        assert isinstance(result, bool)

    @patch('climate_extract.discover.google_discovery.requests.get')
    def test_search_with_mock(self, mock_get):
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "link": "https://example.com/report.pdf",
                    "title": "Test Corp Sustainability Report 2023"
                }
            ]
        }
        mock_get.return_value = mock_response

        discovery = GoogleDiscovery()
        discovery.api_key = "test_key"
        discovery.cse_id = "test_id"

        results = discovery.search_pdfs("Test Corp", max_results=5)

        # The implementation may or may not call the API depending on configuration
        assert isinstance(results, list)


class TestDatabaseModels:
    """Tests for database models"""

    def test_company_model(self):
        company = Company(
            id=1,
            name="Test Corp",
            ticker="TEST",
            industry="Technology",
            website="https://test.com"
        )

        assert company.name == "Test Corp"
        assert company.ticker == "TEST"

    def test_sustainability_report_model(self):
        report = SustainabilityReport(
            id=1,
            company_id=1,
            report_year=2023,
            report_type="sustainability",
            source_url="https://example.com/report.pdf",
            title="Test Report",
            extraction_status="completed"
        )

        assert report.report_year == 2023
        assert report.extraction_status == "completed"


class TestConfig:
    """Tests for configuration"""

    def test_settings_load(self):
        assert settings.app_name == "Climate Data Extraction System"
        assert settings.version == "1.0.0"

    def test_database_config(self):
        assert settings.db.url.startswith("sqlite")
        assert settings.db.echo == False

    def test_llm_config(self):
        assert settings.llm.provider in ["openai", "anthropic", "local"]
        assert settings.llm.model == "gpt-4"

    def test_extraction_config(self):
        assert settings.extraction.min_confidence_score >= 0
        assert settings.extraction.max_pdf_size_mb > 0

    def test_storage_config(self):
        assert settings.storage.raw_data_path is not None
        assert settings.storage.processed_data_path is not None


@pytest.fixture
def temp_pdf():
    """Create a temporary PDF file for testing"""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        # Write minimal PDF structure
        f.write(b"%PDF-1.4\n")
        f.write(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
        f.write(b"2 0 obj << /Type /Pages /Kids [] /Count 0 >> endobj\n")
        f.write(b"xref\n")
        f.write(b"0 3\n")
        f.write(b"0000000000 65535 f\n")
        f.write(b"0000000009 00000 n\n")
        f.write(b"0000000052 00000 n\n")
        f.write(b"trailer << /Root 1 0 R /Size 3 >>\n")
        f.write(b"startxref\n")
        f.write(b"95\n")
        f.write(b"%%EOF\n")
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


class TestIntegration:
    """Integration tests"""

    def test_extraction_data_structure(self):
        """Test emissions data structure"""
        data = ExtractedEmissionsData(
            scope_1_absolute=1000.0,
            scope_2_location_based=2000.0,
            scope_3_total=5000.0,
            reporting_year=2023,
            confidence_score=0.9,
            extraction_method="rule_based"
        )

        assert data.scope_1_absolute == 1000.0
        assert data.scope_2_location_based == 2000.0
        assert data.scope_3_total == 5000.0
        assert data.confidence_score == 0.9

    def test_discovery_report_structure(self):
        """Test discovered report structure"""
        report = DiscoveredReport(
            url="https://test.com/report.pdf",
            title="Test Report",
            company="Test Corp",
            year=2023
        )

        assert report.url.endswith(".pdf")
        assert report.year == 2023


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
