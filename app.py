"""
Climate Data Extraction - Web Application
Professional frontend with one-click extraction
"""

import os
import json
import threading
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, Response
from werkzeug.utils import secure_filename

# Import extraction system
from climate_extract.main import ClimateExtractor

app = Flask(__name__)
app.config['SECRET_KEY'] = 'climate-extract-2024'

# Global state for tracking extractions
extraction_status = {
    "running": False,
    "current_company": None,
    "progress": 0,
    "total": 0,
    "results": [],
    "errors": []
}

# Initialize extractor
extractor = ClimateExtractor(output_dir="./data")


# Top 50 Companies (S&P 500 subset)
TOP_50_COMPANIES = [
    {"name": "Apple", "website": "https://apple.com"},
    {"name": "Microsoft", "website": "https://microsoft.com"},
    {"name": "Amazon", "website": "https://amazon.com"},
    {"name": "Google", "website": "https://google.com"},
    {"name": "Tesla", "website": "https://tesla.com"},
    {"name": "Meta", "website": "https://meta.com"},
    {"name": "Nvidia", "website": "https://nvidia.com"},
    {"name": "Berkshire Hathaway", "website": "https://berkshirehathaway.com"},
    {"name": "Johnson & Johnson", "website": "https://jnj.com"},
    {"name": "Visa", "website": "https://visa.com"},
    {"name": "Walmart", "website": "https://walmart.com"},
    {"name": "JPMorgan Chase", "website": "https://jpmorganchase.com"},
    {"name": "Procter & Gamble", "website": "https://pg.com"},
    {"name": "Mastercard", "website": "https://mastercard.com"},
    {"name": "UnitedHealth", "website": "https://unitedhealthgroup.com"},
    {"name": "Home Depot", "website": "https://homedepot.com"},
    {"name": "Bank of America", "website": "https://bankofamerica.com"},
    {"name": "Chevron", "website": "https://chevron.com"},
    {"name": "Pfizer", "website": "https://pfizer.com"},
    {"name": "ExxonMobil", "website": "https://exxonmobil.com"},
    {"name": "Coca-Cola", "website": "https://coca-cola.com"},
    {"name": "PepsiCo", "website": "https://pepsico.com"},
    {"name": "Costco", "website": "https://costco.com"},
    {"name": "AbbVie", "website": "https://abbvie.com"},
    {"name": "Merck", "website": "https://merck.com"},
    {"name": "Netflix", "website": "https://netflix.com"},
    {"name": "Adobe", "website": "https://adobe.com"},
    {"name": "Salesforce", "website": "https://salesforce.com"},
    {"name": "Cisco", "website": "https://cisco.com"},
    {"name": "Intel", "website": "https://intel.com"},
    {"name": "Nike", "website": "https://nike.com"},
    {"name": "Disney", "website": "https://disney.com"},
    {"name": "Verizon", "website": "https://verizon.com"},
    {"name": "AT&T", "website": "https://att.com"},
    {"name": "Oracle", "website": "https://oracle.com"},
    {"name": "McDonald's", "website": "https://mcdonalds.com"},
    {"name": "IBM", "website": "https://ibm.com"},
    {"name": "Goldman Sachs", "website": "https://goldmansachs.com"},
    {"name": "Morgan Stanley", "website": "https://morganstanley.com"},
    {"name": "Boeing", "website": "https://boeing.com"},
    {"name": "Caterpillar", "website": "https://caterpillar.com"},
    {"name": "3M", "website": "https://3m.com"},
    {"name": "General Electric", "website": "https://ge.com"},
    {"name": "Ford", "website": "https://ford.com"},
    {"name": "General Motors", "website": "https://gm.com"},
    {"name": "Shell", "website": "https://shell.com"},
    {"name": "BP", "website": "https://bp.com"},
    {"name": "TotalEnergies", "website": "https://totalenergies.com"},
    {"name": "Starbucks", "website": "https://starbucks.com"},
    {"name": "Target", "website": "https://target.com"},
]


@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html', companies=TOP_50_COMPANIES)


@app.route('/api/extract', methods=['POST'])
def extract_company():
    """Extract data for a single company"""
    data = request.json
    company_name = data.get('company')
    website = data.get('website')
    max_reports = data.get('max_reports', 3)

    if not company_name:
        return jsonify({"error": "Company name required"}), 400

    try:
        result = extractor.extract_company(
            company_name=company_name,
            website=website,
            max_reports=max_reports
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/extract-batch', methods=['POST'])
def extract_batch():
    """Start batch extraction in background"""
    global extraction_status

    if extraction_status["running"]:
        return jsonify({"error": "Extraction already running"}), 400

    data = request.json
    companies = data.get('companies', TOP_50_COMPANIES[:10])
    max_reports = data.get('max_reports', 2)

    # Start extraction in background
    thread = threading.Thread(
        target=run_batch_extraction,
        args=(companies, max_reports)
    )
    thread.start()

    return jsonify({"status": "started", "total": len(companies)})


def run_batch_extraction(companies, max_reports):
    """Run batch extraction in background"""
    global extraction_status

    extraction_status = {
        "running": True,
        "current_company": None,
        "progress": 0,
        "total": len(companies),
        "results": [],
        "errors": []
    }

    for i, company in enumerate(companies):
        name = company.get('name') if isinstance(company, dict) else company
        website = company.get('website') if isinstance(company, dict) else None

        extraction_status["current_company"] = name
        extraction_status["progress"] = i

        try:
            result = extractor.extract_company(
                company_name=name,
                website=website,
                max_reports=max_reports
            )
            extraction_status["results"].append(result)
        except Exception as e:
            extraction_status["errors"].append({"company": name, "error": str(e)})

    extraction_status["running"] = False
    extraction_status["progress"] = len(companies)


@app.route('/api/status')
def get_status():
    """Get extraction status"""
    return jsonify(extraction_status)


@app.route('/api/reports')
def list_reports():
    """List all downloaded reports"""
    reports_dir = Path("./data/reports")
    reports = []

    if reports_dir.exists():
        for company_dir in reports_dir.iterdir():
            if company_dir.is_dir():
                for pdf in company_dir.glob("*.pdf"):
                    reports.append({
                        "company": company_dir.name,
                        "filename": pdf.name,
                        "size_mb": round(pdf.stat().st_size / 1024 / 1024, 2),
                        "path": str(pdf)
                    })

    return jsonify(reports)


@app.route('/api/download/<company>/<filename>')
def download_report(company, filename):
    """Download a specific report"""
    filepath = Path(f"./data/reports/{company}/{filename}")
    if filepath.exists():
        return send_file(filepath, as_attachment=True)
    return jsonify({"error": "File not found"}), 404


@app.route('/api/companies')
def get_companies():
    """Get list of top 50 companies"""
    return jsonify(TOP_50_COMPANIES)


if __name__ == '__main__':
    # Create templates directory
    os.makedirs('templates', exist_ok=True)

    print("=" * 60)
    print("Climate Data Extraction - Web Interface")
    print("=" * 60)
    print("Open in browser: http://localhost:5000")
    print("=" * 60)

    app.run(debug=True, host='0.0.0.0', port=5000)
