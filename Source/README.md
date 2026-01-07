# OCR Text Extractor

This directory contains a Dockerized Python script for extracting text from scanned PDF documents using OCR.

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
   - `OUTPUT_JSON`: Output JSON filename (debug only)
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
- **Letter boundary detection**: The pipeline uses the LLM to detect where one letter ends and another begins in merged PDF documents
- Missing input PDF or model file will cause startup failures
- GPU mode requires NVIDIA GPU and nvidia-container-toolkit
- **Model loading**: The LLM server has a 60-second startup period to allow for model loading. Larger models may take longer to load; the healthcheck will retry for up to 2 minutes before failing.
- **Healthcheck**: Uses `curl` to check if the llama.cpp server is responding on the `/health` endpoint

## Letter Boundary Detection

The OCR pipeline includes LLM-based letter boundary detection to automatically identify where one letter ends and another begins in a merged PDF document.

### How it works

1. **OCR Extraction**: First, text is extracted from each page using OCRmyPDF
2. **Pairwise Classification**: For each adjacent page pair (i, i+1), the LLM analyzes both pages and decides whether page i+1 starts a new letter
3. **Grouping**: Pages are grouped into letters based on the boundary decisions
4. **Logging**: All decisions are logged with confidence scores and reasoning

### Features

- **Bilingual Support**: Prompts are in German (primary) with English support
- **Deterministic**: Low temperature (0.1) for consistent, non-creative responses
- **Structured Output**: LLM returns JSON with:
  - `boundary`: true if new letter, false if continuation
  - `confidence`: 0.0 to 1.0
  - `reason`: Short explanation for the decision
- **Page 1 Always Starts**: The first page is always treated as the start of a letter

### Output

The pipeline logs:
- Boundary decisions for each page pair
- Confidence scores
- Reasoning
- Final letter groupings (which pages belong to which letter)

No PDF splitting or file output is performed - the feature only logs results.

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
- `--detect-boundaries`: Enable LLM-based letter boundary detection (requires LLM server)
- `--llm-host`: LLM server hostname (default: `llm`)
- `--llm-port`: LLM server port (default: `8080`)
- `--llm-temperature`: LLM sampling temperature (default: `0.1` for deterministic responses)

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
