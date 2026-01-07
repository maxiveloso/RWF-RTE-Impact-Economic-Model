#!/bin/bash
# Setup OCR dependencies for RWF Project
# Run with: bash setup_ocr.sh

echo "================================"
echo "RWF OCR SETUP"
echo "================================"
echo ""

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew not found. Please install from https://brew.sh"
    exit 1
fi

echo "✓ Homebrew found"
echo ""

# Install Tesseract OCR
echo "Installing Tesseract OCR..."
brew install tesseract tesseract-lang

if [ $? -eq 0 ]; then
    echo "✓ Tesseract installed"
else
    echo "⚠ Tesseract installation failed or already installed"
fi

echo ""

# Verify Tesseract installation
TESSERACT_VERSION=$(tesseract --version 2>&1 | head -1)
echo "Tesseract version: $TESSERACT_VERSION"
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
source venv/bin/activate 2>/dev/null || echo "⚠ venv not found, using global Python"

pip install -q pytesseract pdf2image pillow

if [ $? -eq 0 ]; then
    echo "✓ Python packages installed"
else
    echo "❌ Failed to install Python packages"
    exit 1
fi

echo ""
echo "================================"
echo "INSTALLATION COMPLETE"
echo "================================"
echo ""
echo "Test OCR with:"
echo "  python ocr_processor.py sources/MSDE_annual_report_24_25.pdf"
echo ""
