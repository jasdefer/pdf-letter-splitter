# OCR Text Extractor with Positional Data

This directory contains a Dockerized Python script for extracting text with bounding box coordinates from scanned PDF documents using OCR.

The extractor produces TSV (tab-separated values) output with positional data for each OCR element, enabling downstream processing such as letter detection, date/sender extraction, and document splitting.

## Docker Compose Setup (Recommended)

The easiest way to run the OCR pipeline is using Docker Compose, which automatically manages both the OCR pipeline and a local LLM server.

### Prerequisites

The setup requires a llama.cpp server Docker image. You have several options:

1. **Build from llama.cpp source**: Follow [llama.cpp Docker documentation](https://github.com/ggerganov/llama.cpp/tree/master/examples/server#docker) to build the image
2. **Use a pre-built image**: If available, pull from `ghcr.io/ggerganov/llama.cpp:server`
3. **Tag your own build**: If you build llama.cpp locally, tag it appropriately:
   ```bash
   docker tag your-llama-cpp-build ghcr.io/ggerganov/llama.cpp:server
   ```

### Setup

1. Copy the example environment file and edit it:
   ```bash
   cd Source
   cp .env.example .env
   ```

2. Edit `.env` to configure:
   - `INPUT_PDF`: Your input PDF filename (must exist in Source/)
   - `OUTPUT_TSV`: Output TSV filename
   - `MODEL_FILE`: LLM model filename (must exist in Source/)
   - `OCR_JOBS`: Number of parallel OCR jobs (0 = use all CPU cores)
   - `COMPOSE_PROFILES`: Use `cpu` (default) or `gpu`

3. Place your input PDF and model file in the Source/ directory:
   ```bash
   # Example
   cp /path/to/your/document.pdf Source/input.pdf
   cp /path/to/your/model.gguf Source/model.gguf
   ```

### Running

**CPU mode (default):**
```bash
cd Source
docker compose --profile cpu up --abort-on-container-exit
```

**GPU mode (requires nvidia-container-toolkit):**
```bash
cd Source
docker compose --profile gpu up --abort-on-container-exit
```

The pipeline will run once and exit automatically. Both containers stop when the pipeline completes.

### Cleanup

To remove all containers after execution:
```bash
docker compose down --profile cpu
```

### Notes

- The LLM server runs internally and is not exposed to the host
- Pipeline → LLM communication is not yet implemented (infrastructure only)
- Missing input PDF or model file will cause startup failures
- GPU mode requires NVIDIA GPU and nvidia-container-toolkit
- **Model loading**: The LLM server has a 60-second startup period to allow for model loading. Larger models may take longer to load; the healthcheck will retry for up to 2 minutes before failing.
- **Healthcheck**: Uses `curl` to check if the llama.cpp server is responding on the `/health` endpoint

## Building the Docker Image

```bash
cd Source
docker build -t pdf-letter-splitter .
```

## Usage

### Basic Usage (with bind mount)

```bash
docker run --rm -v "$(pwd):/work" pdf-letter-splitter \
  -i Test/test.pdf -o Test/output.tsv
```

### Using Default Arguments

By default, the script looks for `input.pdf` and writes to `output.tsv`:

```bash
docker run --rm -v "$(pwd):/work" pdf-letter-splitter
```

### Command-Line Arguments

- `-i, --input`: Input PDF file path (default: `input.pdf`)
- `-o, --output`: Output TSV file path (default: `output.tsv`)
- `--no-rotate`: Disable automatic page rotation correction (default: enabled)
- `--no-deskew`: Disable deskewing of pages (default: enabled)
- `--jobs`: Number of parallel OCR jobs (0 = use all CPU cores, default: 0)
- `--verbose`: Enable verbose debug logging and dump full OCR table to `ocr_output.tsv`

## Output Format

The script generates a TSV file with the following columns:

### Base Columns (from Tesseract)

- `level`: OCR hierarchy level (1=page, 2=block, 3=paragraph, 4=line, 5=word)
- `page_num`: Page number (1-indexed)
- `block_num`: Block number within page
- `par_num`: Paragraph number within block
- `line_num`: Line number within paragraph
- `word_num`: Word number within line
- `left`: Left coordinate (pixels)
- `top`: Top coordinate (pixels)
- `width`: Width (pixels)
- `height`: Height (pixels)
- `conf`: Confidence score (-1 for non-leaf elements, 0-100 for words)
- `text`: Extracted text

### Derived Columns

- `right`: Right coordinate (pixels) = left + width
- `bottom`: Bottom coordinate (pixels) = top + height
- `page_width`: Page width in pixels (same for all rows on a page)
- `page_height`: Page height in pixels (same for all rows on a page)

Example TSV output:

```tsv
level	page_num	block_num	par_num	line_num	word_num	left	top	width	height	conf	text	right	bottom	page_width	page_height
1	1	0	0	0	0	0	0	5167	7309	-1.0		5167	7309	5167	7309
5	1	1	1	1	1	209	420	72	21	96.5	Hello	281	441	5167	7309
5	1	1	1	1	2	287	420	58	21	97.0	World	345	441	5167	7309
```

### Verbose Mode

When `--verbose` is specified:
- Logging level is set to DEBUG
- Full OCR table is dumped to `ocr_output.tsv` in the working directory

## Features

- **OCR Language Support**: German and English (`deu+eng`)
- **OCRmyPDF Integration**: Uses ocrmypdf to create searchable PDFs with forced OCR on all pages
- **Tesseract TSV Output**: Extracts text with bounding box coordinates for positional analysis
- **Automatic Corrections**: 
  - Page rotation correction (can be disabled with `--no-rotate`)
  - Deskewing of skewed pages (can be disabled with `--no-deskew`)
- **Parallel Processing**: Uses all available CPU cores by default for faster OCR
- **Derived Columns**: Automatically computes right/bottom coordinates and page dimensions
- **Verbose Logging**: Optional DEBUG-level logs and full OCR dump with `--verbose`
- **Robust Extraction**: Handles multi-page PDFs with comprehensive positional data
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
- poppler-utils (for PDF manipulation)
- Python packages: pandas, pytesseract, Pillow, pypdf
