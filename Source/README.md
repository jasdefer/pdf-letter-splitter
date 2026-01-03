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
- `--no-rotate`: Disable automatic page rotation correction (default: enabled)
- `--no-deskew`: Disable deskewing of pages (default: enabled)
- `--jobs`: Number of parallel OCR jobs (0 = use all CPU cores, default: 0)

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
- **OCRmyPDF Integration**: Uses ocrmypdf to create searchable PDFs with forced OCR on all pages
- **Automatic Corrections**: 
  - Page rotation correction (can be disabled with `--no-rotate`)
  - Deskewing of skewed pages (can be disabled with `--no-deskew`)
- **Parallel Processing**: Uses all available CPU cores by default for faster OCR
- **Text Normalization**: Applies minimal whitespace cleanup
  - Trims trailing spaces per line
  - Collapses multiple spaces/tabs into single space
  - Reduces excessive blank lines
  - Trims leading/trailing whitespace per page
- **Robust Text Extraction**: Handles cases where text extraction returns None
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
- OCRmyPDF with Tesseract OCR
- German and English language packs for Tesseract
- Python package: pypdf
