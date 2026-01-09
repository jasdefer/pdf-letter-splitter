# PDF Letter Splitter

This directory contains a Dockerized pipeline for processing PDFs with multiple letters: extracting text via OCR and segmenting into individual letters with metadata extraction.

## What This Pipeline Does

The complete workflow includes:

1. **OCR Text Extraction** - Extracts text from scanned PDF pages using OCRmyPDF with German and English support
2. **Letter Segmentation** - Identifies letter boundaries using header scoring heuristics
3. **Metadata Extraction** - Extracts date, sender, and topic from each letter's first page
4. **Structured Output** - Returns JSON with complete letter information

## Docker Compose Setup (Recommended)

The easiest way to run the complete pipeline is using Docker Compose, which automatically manages both the OCR pipeline and a local LLM server.

### Prerequisites

The setup requires a llama.cpp server Docker image. You have several options:

1. **Build from llama.cpp source**: Follow [llama.cpp Docker documentation](https://github.com/ggerganov/llama.cpp/tree/master/examples/server#docker) to build the image
2. **Use a pre-built image**: If available, pull from `ghcr.io/ggerganov/llama.cpp:server`
3. **Tag your own build**: If you build llama.cpp locally, tag it appropriately:
   
   **Bash:**
   ```bash
   docker tag your-llama-cpp-build ghcr.io/ggerganov/llama.cpp:server
   ```
   
   **PowerShell:**
   ```powershell
   docker tag your-llama-cpp-build ghcr.io/ggerganov/llama.cpp:server
   ```

### Setup

1. Copy the example environment file and edit it:
   
   **Bash:**
   ```bash
   cd Source
   cp .env.example .env
   ```
   
   **PowerShell:**
   ```powershell
   cd Source
   Copy-Item .env.example .env
   ```

2. Edit `.env` to configure:
   - `INPUT_PDF`: Your input PDF filename (must exist in Source/)
   - `OUTPUT_JSON`: Output JSON filename with complete results (default: results.json)
   - `MODEL_FILE`: LLM model filename (must exist in Source/)
   - `OCR_JOBS`: Number of parallel OCR jobs (0 = use all CPU cores)
   - `COMPOSE_PROFILES`: Use `cpu` (default) or `gpu`

3. Place your input PDF and model file in the Source/ directory:
   
   **Bash:**
   ```bash
   # Example
   cp /path/to/your/document.pdf Source/input.pdf
   cp /path/to/your/model.gguf Source/model.gguf
   ```
   
   **PowerShell:**
   ```powershell
   # Example
   Copy-Item C:\path\to\your\document.pdf Source\input.pdf
   Copy-Item C:\path\to\your\model.gguf Source\model.gguf
   ```

### Running

**CPU mode (default):**

**Bash:**
```bash
cd Source
docker compose --profile cpu up --abort-on-container-exit
```

**PowerShell:**
```powershell
cd Source
docker compose --profile cpu up --abort-on-container-exit
```

**GPU mode (requires nvidia-container-toolkit):**

**Bash:**
```bash
cd Source
docker compose --profile gpu up --abort-on-container-exit
```

**PowerShell:**
```powershell
cd Source
docker compose --profile gpu up --abort-on-container-exit
```

The pipeline will run once and exit automatically. Both containers stop when the pipeline completes.

### Cleanup

To remove all containers after execution:

**Bash:**
```bash
docker compose down --profile cpu
```

**PowerShell:**
```powershell
docker compose down --profile cpu
```

### Output Format

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

### Notes

- The LLM server runs internally and is not exposed to the host
- Pipeline → LLM communication is not yet implemented (infrastructure only)
- Missing input PDF or model file will cause startup failures
- GPU mode requires NVIDIA GPU and nvidia-container-toolkit
- **Model loading**: The LLM server has a 60-second startup period to allow for model loading. Larger models may take longer to load; the healthcheck will retry for up to 2 minutes before failing.
- **Healthcheck**: Uses `curl` to check if the llama.cpp server is responding on the `/health` endpoint

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

## Direct Docker Usage (Alternative to Docker Compose)

### Basic Usage (with bind mount)

Process a PDF and output complete results with letter segmentation:

**Bash:**
```bash
docker run --rm -v "$(pwd):/work" pdf-letter-splitter \
  -i input.pdf -o results.json
```

**PowerShell:**
```powershell
docker run --rm -v "${PWD}:/work" pdf-letter-splitter `
  -i input.pdf -o results.json
```

### Verbose Output

Get detailed progress information:

**Bash:**
```bash
docker run --rm -v "$(pwd):/work" pdf-letter-splitter \
  -i input.pdf -o results.json --verbose
```

**PowerShell:**
```powershell
docker run --rm -v "${PWD}:/work" pdf-letter-splitter `
  -i input.pdf -o results.json --verbose
```

### Command-Line Arguments

The unified pipeline (`process_letters.py`) supports:

- `-i, --input`: Input PDF file path (required)
- `-o, --output`: Output JSON file path (default: `output.json`)
- `--no-rotate`: Disable automatic page rotation correction (default: enabled)
- `--no-deskew`: Disable deskewing of pages (default: enabled)
- `--jobs`: Number of parallel OCR jobs (0 = use all CPU cores, default: 0)
- `--verbose`: Print detailed progress information

## Pipeline Components

The Docker container includes three Python modules that work together:

1. **`extract_text.py`** - OCR text extraction from PDF pages
2. **`analyze_letters.py`** - Letter segmentation and metadata extraction
3. **`process_letters.py`** - Unified entry point orchestrating the complete workflow

## Features

- **Complete Workflow**: PDF → OCR → Segmentation → Letter Metadata in one command
- **OCR Language Support**: German and English (`deu+eng`)
- **OCRmyPDF Integration**: Uses ocrmypdf to create searchable PDFs with forced OCR on all pages
- **Letter Segmentation**: Automatic boundary detection using header scoring heuristics
- **Metadata Extraction**: Extracts date, sender, and topic from each letter
- **Automatic Corrections**: 
  - Page rotation correction (can be disabled with `--no-rotate`)
  - Deskewing of skewed pages (can be disabled with `--no-deskew`)
- **Parallel Processing**: Uses all available CPU cores by default for faster OCR
- **Text Normalization**: Applies minimal whitespace cleanup
  - Trims trailing spaces per line
  - Collapses multiple spaces/tabs into single space
  - Reduces excessive blank lines
  - Trims leading/trailing whitespace per page
- **Robust Error Handling**: Exits with non-zero code on failures

## Running Tests

Tests are located in the `Test/` directory and can be run using unittest:

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

## Requirements

The Docker image includes:
- Python 3.11
- OCRmyPDF with Tesseract OCR
- German and English language packs for Tesseract
- Python package: pypdf
- All three pipeline modules (extract_text.py, analyze_letters.py, process_letters.py)

## Complete Letter Processing Pipeline

The `process_letters.py` script provides a unified entry point that combines OCR text extraction and letter segmentation into one workflow.

### Quick Start

```bash
# Process a PDF with multiple letters
python process_letters.py -i input.pdf -o results.json

# With verbose output
python process_letters.py -i input.pdf -o results.json --verbose

# Customize OCR options
python process_letters.py -i input.pdf -o results.json --no-rotate --jobs 4
```

### Output Format

The complete pipeline outputs a JSON file with the following structure:

```json
{
  "input_file": "letters.pdf",
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

### Command-Line Options

- `-i, --input`: Input PDF file path (required)
- `-o, --output`: Output JSON file path (default: output.json)
- `--no-rotate`: Disable automatic page rotation correction
- `--no-deskew`: Disable deskewing of pages
- `--jobs`: Number of parallel OCR jobs (0 = use all CPU cores)
- `--verbose`: Print detailed progress information

### Python API

```python
from process_letters import process_pdf_letters
from pathlib import Path

# Process the PDF
result = process_pdf_letters(
    Path('input.pdf'),
    rotate=True,
    deskew=True,
    jobs=0
)

print(f"Found {result['letters_found']} letters in {result['total_pages']} pages")
for letter in result['letters']:
    print(f"Letter from {letter['sender']}: {letter['topic']}")
```

## Letter Segmentation and Analysis

The `analyze_letters.py` module provides rule-based letter segmentation and metadata extraction from OCR text output.

### Features

- **Automatic Letter Detection**: Identifies letter boundaries using header scoring heuristics
- **Metadata Extraction**: Extracts date, sender, and topic from each letter
- **Multi-format Date Support**: Handles ISO, European (DD.MM.YYYY), US (MM/DD/YYYY), and named month formats in German and English
- **Organization Recognition**: Identifies companies (GmbH, Inc, Ltd, etc.) and government offices
- **Bilingual Support**: Works with both German and English correspondence

### Usage

#### Recommended: Use the Unified Pipeline

For most use cases, use `process_letters.py` which combines both steps:

```python
from process_letters import process_pdf_letters

result = process_pdf_letters('input.pdf')
# Returns complete results with letters and metadata
```

#### As Separate Python Modules

For advanced use cases, you can use the modules independently:

```python
from extract_text import extract_text_from_pdf
from analyze_letters import analyze_documents

# Extract text from PDF
result = extract_text_from_pdf('input.pdf')
ocr_pages = [page['text'] for page in result['pages']]

# Analyze and segment letters
letters = analyze_documents(ocr_pages)

for letter in letters:
    print(f"Letter starting at page {letter['start_page']}:")
    print(f"  Date: {letter['date']}")
    print(f"  Sender: {letter['sender']}")
    print(f"  Topic: {letter['topic']}")
    print(f"  Pages: {letter['page_count']}")
```

#### Command-Line Usage

```bash
python3 analyze_letters.py input.pdf > output.json
```

### Output Format

The `analyze_documents()` function returns a list of dictionaries:

```json
[
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
```

### How It Works

1. **Header Scoring**: Each page receives a score based on indicators like:
   - Date in top 15% of page (+30 points)
   - Sender/organization name (+20 points)
   - Subject line (+15 points)
   - Formal salutation (+15 points)
   - "Page 1 of X" markers (+25 points)

2. **Boundary Detection**: Pages with scores ≥40 are considered new letter starts

3. **Metadata Extraction**: The first page of each letter is analyzed using specialized regex patterns and heuristics

### Testing

```bash
# Run unit tests
python3 -m unittest Test.test_analyze_letters -v

# Run integration test
python3 Test/test_integration.py
```
