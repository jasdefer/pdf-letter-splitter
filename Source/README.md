# PDF Letter Splitter

A Dockerized tool for processing scanned PDFs containing multiple letters. The pipeline extracts text via OCR and automatically segments pages into individual letters with metadata extraction.

## Overview

The PDF Letter Splitter processes multi-page scanned PDFs and:

1. **Extracts text** from each page using OCRmyPDF with German and English language support
2. **Segments pages** into individual letters using header scoring heuristics
3. **Extracts metadata** (date, sender, topic) from each letter's first page
4. **Outputs structured JSON** with complete letter information

## Building the Docker Image

**Bash:**
```bash
cd Source
docker build -t pdf-letter-splitter .
```

**PowerShell:**
```powershell
cd Source
docker build -t pdf-letter-splitter .
```

## Usage

### Basic Usage

Process a PDF and output results with letter segmentation:

**Bash:**
```bash
docker run --rm -v "$(pwd):/work" pdf-letter-splitter \
  -i /work/input.pdf -o /work/results.json
```

**PowerShell:**
```powershell
docker run --rm -v "${PWD}:/work" pdf-letter-splitter `
  -i /work/input.pdf -o /work/results.json
```

### With Verbose Output

Get detailed progress information:

**Bash:**
```bash
docker run --rm -v "$(pwd):/work" pdf-letter-splitter \
  -i /work/input.pdf -o /work/results.json --verbose
```

**PowerShell:**
```powershell
docker run --rm -v "${PWD}:/work" pdf-letter-splitter `
  -i /work/input.pdf -o /work/results.json --verbose
```

### Command-Line Arguments

- `-i, --input`: Input PDF file path (required)
- `-o, --output`: Output JSON file path (default: output.json)
- `--no-rotate`: Disable automatic page rotation correction
- `--no-deskew`: Disable deskewing of pages
- `--jobs`: Number of parallel OCR jobs (0 = use all CPU cores, default: 0)
- `--verbose`: Print detailed progress information

## Output Format

The pipeline generates a JSON file with the following structure:

```json
{
  "input_file": "input.pdf",
  "total_pages": 5,
  "letters_found": 2,
  "letters": [
    {
      "date": "2026-01-15",
      "sender": "Finanzamt München",
      "topic": "Steuerbescheid 2025",
      "page_count": 2,
      "start_page": 1
    },
    {
      "date": "2026-01-20",
      "sender": "TechCorp GmbH",
      "topic": "Annual Report 2025",
      "page_count": 3,
      "start_page": 3
    }
  ]
}
```

## Features

- **Complete Workflow**: PDF → OCR → Segmentation → Letter Metadata in one command
- **OCR Language Support**: German and English (`deu+eng`)
- **Letter Segmentation**: Automatic boundary detection using header scoring heuristics
- **Metadata Extraction**: Extracts date, sender, and topic from each letter
- **Automatic Corrections**: 
  - Page rotation correction (can be disabled with `--no-rotate`)
  - Deskewing of skewed pages (can be disabled with `--no-deskew`)
- **Parallel Processing**: Uses all available CPU cores by default for faster OCR
- **Text Normalization**: Applies minimal whitespace cleanup
- **Robust Error Handling**: Exits with non-zero code on failures

## How It Works

### Letter Segmentation

The tool uses header scoring to detect letter boundaries. Each page is scored based on:

- **Date in top 15%** of page (+30 points)
- **Sender/organization found** (+20 points)
- **Subject line present** (+15 points)
- **Formal salutation detected** (+15 points)
- **"Page 1 of X" markers** (+25 points)
- **Address block structure** (+10 points)

Pages scoring ≥40 points are considered the start of a new letter.

### Metadata Extraction

For each detected letter, the first page is analyzed to extract:

- **Date**: Supports ISO (YYYY-MM-DD), European (DD.MM.YYYY), US (MM/DD/YYYY), and named month formats in German and English
- **Sender**: Identifies companies (GmbH, Inc, Ltd, etc.), government offices (Finanzamt, etc.), and individuals
- **Topic**: Matches explicit subject markers (Subject:, Betreff:, RE:) or falls back to ALL CAPS/capitalized headings

## Docker Image Contents

The Docker image includes:

- Python 3.11
- OCRmyPDF with Tesseract OCR
- German and English language packs for Tesseract
- Python package: pypdf
- Complete pipeline: `process_letters.py` (entry point), `extract_text.py`, `analyze_letters.py`

## Module Structure

The codebase is organized into three Python modules:

- **`process_letters.py`**: Main entry point that orchestrates the complete workflow
- **`extract_text.py`**: OCR text extraction from PDF pages (called by process_letters.py)
- **`analyze_letters.py`**: Letter segmentation and metadata extraction (called by process_letters.py)

Only `process_letters.py` should be run directly. The other modules are for code organization and are imported as needed.

## Running Tests

Tests can be run inside the Docker container:

**Bash:**
```bash
docker run --rm --entrypoint bash -v "$(pwd):/work" pdf-letter-splitter \
  -c "cd /work && python3 -m unittest discover -s Test -p 'test_*.py' -v"
```

**PowerShell:**
```powershell
docker run --rm --entrypoint bash -v "${PWD}:/work" pdf-letter-splitter `
  -c "cd /work && python3 -m unittest discover -s Test -p 'test_*.py' -v"
```

## Design Decisions

- **European date format** (DD.MM.YYYY) is prioritized over US format for German document handling
- **Date validation** rejects calendar-invalid dates (e.g., February 31)
- **Smart sender detection** skips the first 2 sender-like lines when searching for topics to avoid false matches
- **Returns `None`** for missing metadata rather than empty strings for clarity
