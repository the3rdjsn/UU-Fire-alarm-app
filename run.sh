#!/bin/bash
# UofU Fire Alarm Management System — Launch Script
# ─────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  ██████╗ ██╗   ██╗ ██████╗ ██╗   ██╗"
echo "  ██╔══██╗╚██╗ ██╔╝██╔═══██╗██║   ██║"
echo "  ██████╔╝ ╚████╔╝ ██║   ██║██║   ██║"
echo "  ██╔══██╗  ╚██╔╝  ██║   ██║██║   ██║"
echo "  ██║  ██║   ██║   ╚██████╔╝╚██████╔╝"
echo ""
echo "  Fire Alarm Management System"
echo "  University of Utah — Facilities Management"
echo "  ─────────────────────────────────────────"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install Python 3.9+ first."
    exit 1
fi

# Install deps if needed
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "Installing dependencies..."
    pip3 install -r requirements.txt --quiet
fi

echo "  Starting app at http://localhost:8501"
echo "  Press Ctrl+C to stop"
echo ""

streamlit run app.py \
    --server.port 8501 \
    --server.headless false \
    --browser.gatherUsageStats false \
    --theme.primaryColor "#CC2929" \
    --theme.backgroundColor "#ffffff" \
    --theme.secondaryBackgroundColor "#f8f8f8" \
    --theme.textColor "#1a1a1a"
