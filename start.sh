#!/bin/bash
# ============================================================
# Climate Data Extraction System - One-Click Setup
# Run this script to install and start the application
# ============================================================

echo ""
echo "============================================================"
echo "   CLIMATE DATA EXTRACTION SYSTEM - SETUP"
echo "============================================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed!"
    echo "Please install Python 3.11+ first"
    exit 1
fi

echo "[OK] Python found: $(python3 --version)"
echo ""

# Create virtual environment if not exists
if [ ! -d ".venv" ]; then
    echo "[SETUP] Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "[SETUP] Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "[SETUP] Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo "[SETUP] Installing dependencies..."
pip install -r requirements.txt --quiet

# Create data directories
mkdir -p data/reports

echo ""
echo "============================================================"
echo "   SETUP COMPLETE - Starting Application"
echo "============================================================"
echo ""
echo "   Open in browser: http://localhost:5000"
echo ""
echo "   Press Ctrl+C to stop the server"
echo "============================================================"
echo ""

# Start the application
python app.py
