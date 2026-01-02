# OCR Text Extractor

This directory contains a Dockerized Python script for extracting text from scanned PDF documents using OCR.

## Building the Docker Image

```bash
cd Source
docker build -t pdf-letter-splitter .
```

## Usage

### Basic Usage (with bind mount)

```bash
docker run --rm -v "$(pwd):/work" pdf-letter-splitter \
  -i Test/test.pdf -o Test/output.json
```

### Using Default Arguments

By default, the script looks for `input.pdf` and writes to `output.json`:

```bash
docker run --rm -v "$(pwd):/work" pdf-letter-splitter
```

### Command-Line Arguments

- `-i, --input`: Input PDF file path (default: `input.pdf`)
- `-o, --output`: Output JSON file path (default: `output.json`)

## Output Format

The script generates a JSON file with the following structure:

```json
{
  "page_count": 4,
  "pages": [
    {
      "page_number": 1,
      "text": "Extracted text from page 1..."
    },
    {
      "page_number": 2,
      "text": "Extracted text from page 2..."
    }
  ]
}
```

## Features

- **OCR Language Support**: German and English (`deu+eng`)
- **High Resolution**: Renders PDF pages at 300 DPI for optimal OCR accuracy
- **Text Normalization**: Applies minimal whitespace cleanup
  - Trims trailing spaces per line
  - Collapses multiple spaces/tabs into single space
  - Reduces excessive blank lines
  - Trims leading/trailing whitespace per page
- **PDF Repair**: Automatically attempts to repair corrupted PDFs using:
  - mutool (MuPDF)
  - qpdf
  - ghostscript
- **Error Handling**: Exits with non-zero code on failures

## Running Tests

Tests are located in the `Test/` directory and can be run using pytest:

```bash
docker run --rm --entrypoint bash -v "$(pwd):/work" pdf-letter-splitter \
  -c "pip install pytest && cd /work && python3 -m pytest Test/test_ocr_extract.py -v"
```

## Requirements

The Docker image includes:
- Python 3.11
- Tesseract OCR with German and English language packs
- Poppler utilities (for PDF rendering)
- PDF repair tools (ghostscript, qpdf, mupdf-tools)
- Python packages: pdf2image, pytesseract, pillow
