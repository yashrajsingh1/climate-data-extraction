# Climate Data Extraction System

A production-grade automated system for discovering, downloading, and extracting emissions data from company sustainability reports at scale.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Project Highlights

- End-to-end ESG pipeline: discovery, download, extraction, and structured output
- Dual interface support: production-ready Flask dashboard and CLI workflows
- Designed for scale: batch processing for S&P 500-style company lists
- Hybrid extraction approach: deterministic rules with optional LLM fallback
- CI-enabled repository with test automation via GitHub Actions

## Overview

This system automatically:
- **Discovers** sustainability/ESG PDF reports from company websites and search engines
- **Downloads** all relevant climate reports (current + historical)
- **Extracts** key emissions data (Scope 1, 2, 3) using intelligent parsing
- **Scales** to process hundreds of companies (S&P 500 level)

## Quick Start

### Windows
```batch
# Double-click or run:
start.bat
```

### Linux/Mac
```bash
chmod +x start.sh
./start.sh
```

### Manual Setup
```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run application
python app.py
```

Then open **http://localhost:5000** in your browser.

## Frontend UI

### Live Demo
Access the web interface at: **http://localhost:5000** after running `python app.py` or `start.bat`

### Preview
The application features a modern, gradient-based dashboard with real-time updates:

![Climate Extract Dashboard](https://via.placeholder.com/800x500/0a0f1e/6366f1?text=Modern+Dashboard+with+Glassmorphism+Design)
*Professional web interface with real-time progress tracking and interactive results*

### Key Features
- ** Modern Design** - Clean, gradient-based UI with glassmorphism effects
- ** Real-Time Updates** - Live progress tracking with auto-refresh
- ** Interactive Dashboard** - View all extracted data in sortable tables
- ** One-Click Actions** - Extract single companies or process batches instantly
- ** Direct Downloads** - Download PDFs directly from the interface
- ** Responsive** - Works on desktop, tablet, and mobile devices

### Interface Components

**1. Extraction Panel**
- Quick search: Enter any company name and click "Extract Data"
- Batch processing: Pre-configured buttons for Top 10 or Top 50 companies
- Progress bar: Real-time updates during extraction
- Status messages: Clear feedback on current operations

**2. Results Section**
- **Emissions Table**: View Scope 1, 2, 3 data with confidence scores
- **Downloaded Files**: Browse all PDFs with direct download links
- **Company Stats**: Quick overview of processed companies
- **Export Options**: Download results as JSON

**3. Navigation**
- Sticky header with branding
- Quick access to all features
- Status indicators for active extractions

### Technology Stack
- **Frontend**: HTML5, CSS3 (Glassmorphism design), Vanilla JavaScript
- **Backend**: Flask + Python 3.11+
- **Real-time**: AJAX polling for status updates
- **Fonts**: Plus Jakarta Sans for modern typography
- **Icons**: SVG graphics with gradient fills

### UI Highlights
```
┌──────────────────────────────────────────────┐
│  ClimateExtract                           │  ← Sticky Navbar
├──────────────────────────────────────────────┤
│  Extract Climate Data                        │
│  ┌────────────────────────────────────────┐ │
│  │ Company Name: [___________] [Extract] │ │  ← Quick Search
│  └────────────────────────────────────────┘ │
│                                              │
│  Batch Actions:                              │
│  [Top 10 Companies] [All 50 Companies]      │  ← One-Click Batch
│                                              │
│  ━━━━━━━━━━━━━━━━ 67% ━━━━━━━━━━━━━━━━     │  ← Progress Bar
│  Processing: Microsoft... (3/10)             │
│                                              │
├──────────────────────────────────────────────┤
│   Extracted Emissions Data                │
│  ┌────────────────────────────────────────┐ │
│  │ Company  │ Year │ Scope1 │ Scope2 │... │ │  ← Results Table
│  │ Tesla    │ 2024 │ 55.2K  │ 1.2M   │... │ │
│  │ Apple    │ 2024 │ 45.8K  │ 980K   │... │ │
│  └────────────────────────────────────────┘ │
│                                              │
│   Downloaded Reports (12 files)           │
│  • apple_2024.pdf (20 MB) [Download]        │  ← File Manager
│  • tesla_2024.pdf (18 MB) [Download]        │
└──────────────────────────────────────────────┘
```

### Color Scheme
- **Primary**: Indigo gradient (#6366f1 → #818cf8)
- **Accent**: Cyan (#22d3ee) for highlights
- **Success**: Emerald (#10b981) for completed actions
- **Background**: Dark navy with gradient overlays
- **Glass Effects**: Semi-transparent cards with backdrop blur

## Features

### Web Interface
- **One-Click Extraction** - Enter company name and extract with single button
- **Batch Processing** - Process Top 10 or all 50 companies at once
- **Real-Time Progress** - Live progress tracking for all operations
- **Results Dashboard** - View extracted emissions data in table format
- **File Downloads** - Download any extracted PDF directly

### CLI Interface
```bash
# Single company
python run.py Tesla --max 5

# With website hint
python run.py Microsoft --website https://microsoft.com

# Batch processing
python run.py --batch companies.json --output results.json

# Save results
python run.py Apple --output apple_data.json
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Interface (Flask)                     │
│                    http://localhost:5000                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   ClimateExtractor (Main)                    │
│                      src/climate_extract/main.py             │
└─────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
┌───────────────────┐ ┌───────────────┐ ┌───────────────────┐
│ UnifiedDiscovery  │ │ PDFDownloader │ │  HybridExtractor  │
│                   │ │               │ │                   │
│ • Google Search   │ │ • Retry Logic │ │ • Rule-based      │
│ • DuckDuckGo      │ │ • Size Check  │ │ • Regex Patterns  │
│ • Playwright      │ │ • Dedup       │ │ • LLM Fallback    │
└───────────────────┘ └───────────────┘ └───────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     SQLite Database                          │
│                     data/climate_data.db                     │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
climate-data-extraction/
├── app.py                      # Web application (Flask)
├── run.py                      # CLI interface
├── start.bat                   # Windows one-click setup
├── start.sh                    # Linux/Mac one-click setup
├── requirements.txt            # Python dependencies
├── templates/
│   └── index.html              # Web dashboard UI
├── src/climate_extract/
│   ├── __init__.py             # Package exports
│   ├── main.py                 # Core extraction logic
│   ├── discover/
│   │   ├── __init__.py
│   │   └── google_discovery.py # PDF discovery engine
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── hybrid_extractor.py # Data extraction
│   │   └── llm_extractor.py    # LLM fallback
│   ├── parse/
│   │   └── pdf_parser.py       # PDF text extraction
│   ├── scraper/
│   │   └── playwright_scraper.py # JavaScript rendering
│   ├── core/
│   │   ├── config.py           # Configuration
│   │   ├── database.py         # Database operations
│   │   └── models.py           # Data models
│   └── utils/
│       └── logging.py          # Logging setup
├── data/
│   └── reports/                # Downloaded PDFs
│       ├── apple/
│       ├── microsoft/
│       ├── tesla/
│       └── ...
└── tests/
    └── test_climate_extract.py # Unit tests
```

## Configuration

### Environment Variables (Optional)

```bash
# Google Custom Search API (improves discovery)
GOOGLE_API_KEY=your_api_key
GOOGLE_CSE_ID=your_search_engine_id

# OpenAI API (enables LLM extraction fallback)
OPENAI_API_KEY=your_openai_key
```

### Getting Google API Keys (Free)

1. **API Key**: https://console.cloud.google.com/apis/credentials
   - Create project → Create credentials → API Key

2. **Search Engine ID**: https://programmablesearchengine.google.com/
   - Add → Search entire web → Create → Copy ID

## Output Format

### JSON Output
```json
{
  "company": "Apple",
  "status": "success",
  "reports_found": 3,
  "reports_downloaded": 3,
  "reports_extracted": 2,
  "emissions_data": [
    {
      "year": 2024,
      "scope_1": 55200,
      "scope_2_location": 1224500,
      "scope_2_market": null,
      "scope_3": null,
      "unit": "tCO2e",
      "confidence": 0.85,
      "source_url": "https://..."
    }
  ],
  "duration_seconds": 45.2
}
```

### Downloaded Files
```
data/reports/apple/
├── apple_2024_abc123.pdf    (20 MB)
├── apple_2023_def456.pdf    (18 MB)
└── apple_2022_ghi789.pdf    (15 MB)
```

## Supported Companies

Pre-configured with Top 50 S&P 500 companies including:
- Technology: Apple, Microsoft, Google, Amazon, Meta, Nvidia
- Finance: JPMorgan, Visa, Mastercard, Goldman Sachs
- Energy: ExxonMobil, Chevron, Shell, BP
- Consumer: Walmart, Coca-Cola, Nike, McDonald's
- Healthcare: Johnson & Johnson, Pfizer, Merck

## API Reference

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web dashboard |
| `/api/extract` | POST | Extract single company |
| `/api/extract-batch` | POST | Start batch extraction |
| `/api/status` | GET | Get extraction status |
| `/api/reports` | GET | List downloaded reports |
| `/api/download/<company>/<file>` | GET | Download specific PDF |
| `/api/companies` | GET | Get company list |

### Python API

```python
from climate_extract import extract_company, extract_batch

# Single company
result = extract_company("Tesla", max_reports=5)

# Multiple companies
companies = [
    {"name": "Apple", "website": "https://apple.com"},
    {"name": "Microsoft"}
]
results = extract_batch(companies)
```

## Performance

| Metric | Value |
|--------|-------|
| Average extraction time | 30-60 seconds per company |
| PDFs per company | 2-5 typically |
| Success rate | 85%+ |
| Supported formats | PDF (any size) |

## Troubleshooting

### Common Issues

**No PDFs found**
- Some companies block automated requests
- Try adding the company website URL
- Enable Playwright for JavaScript-heavy sites

**403 Forbidden errors**
- Company server blocking requests
- This is normal - system will skip and continue

**Extraction shows low confidence**
- PDF may not contain standard emissions tables
- Consider enabling LLM fallback with OpenAI key

## License

MIT License - See LICENSE file for details.

## Author

Climate Data Extraction System - Built for automated ESG data collection at scale.
