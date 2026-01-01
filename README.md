# pdf-letter-splitter

`pdf-letter-splitter` is a Dockerized tool that takes a **single scanned PDF containing multiple letters** and automatically splits it into **one PDF per letter**.

Each output PDF contains all pages belonging to exactly one letter and is named based on metadata extracted from the document.

The tool is designed to be **best-effort, fully automatic, and non-interactive**.

**NEW:** Filenames are now **cleaned and normalized** using a local LLM for better readability.

---

## What this tool does

* Accepts a scanned, multi-page PDF
* Runs OCR on the full document (German and English)
* Detects where one letter ends and the next begins
* Extracts basic metadata from the first page of each letter:

  * Date
  * Sender
  * Topic
* **Normalizes sender and topic names** using a local LLM (optional)
* Writes one PDF per detected letter

No manual review step is included by design.

---

## Output naming

Each output file is written to a flat output directory.

### Fully recognized letters

If all fields are successfully extracted:

```
YYYY-MM-DD-Sender-Topic.pdf
```

Example:

```
2024-11-05-Finanzamt-Mahnung.pdf
```

**With LLM normalization enabled:**
- Sender: Shortened to max 3 words (e.g., "Deutsche Bank" instead of "Deutsche Bank AG Filiale München")
- Topic: Human-readable, max 4 words (e.g., "Jahresabrechnung" instead of "Abrechnung-2024-Ref-12345")

### Partially or unrecognized letters

If **any** of the fields (date, sender, topic) cannot be extracted:

```
XXX-XXX-XXX-01.pdf
XXX-XXX-XXX-02.pdf
...
```

Rules:

* `XXX` is always used for missing or unreliable metadata
* The numeric suffix is incremented **only** for these unrecognized files
* Fully recognized files never receive a suffix

---

## Language and OCR behavior

* OCR is applied to the entire input PDF once
* Supported languages:

  * German
  * English
* Language detection is automatic
* German is preferred when ambiguity exists
* The input PDF’s resolution (DPI) is preserved

---

## Logging and transparency

All processing decisions are written to standard output, including:

* Detected letter start pages
* Heuristics that triggered splits
* Extracted metadata per letter
* Final output filenames

No manifest or sidecar files are generated.

---

## Usage (Docker Compose - Recommended with LLM)

The recommended way to use this tool is with Docker Compose. **The model is embedded in the Docker image** - you download it once during setup, then everything works offline.

### One-Time Setup

```bash
# Step 1: Download the model (~650 MB, takes a few minutes)
./download-model.sh

# Step 2: Build the Docker images (embeds the model)
docker-compose build
```

That's it! The model is now embedded in the image. No additional setup or downloads needed.

### Process PDFs

```bash
# Process your PDFs
docker-compose run --rm pdf-splitter /input/input.pdf /output
```

The LLM server will start automatically with the embedded model and normalize sender/topic names for cleaner filenames.

### GPU Support

If you have an NVIDIA GPU with Docker GPU support:

1. Install [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
2. Download the model: `./download-model.sh`
3. Build with GPU support: `docker-compose -f docker-compose.gpu.yml build`
4. Run: `docker-compose -f docker-compose.gpu.yml run --rm pdf-splitter /input/input.pdf /output`

### Using a Different Model

To use a different model (e.g., better quality):

```bash
# Download a different model
./download-model.sh llama32  # or phi3 for best quality

# Rebuild to embed the new model
docker-compose build
```

---

## Usage (Docker standalone - Without LLM)

If you don't want to use the LLM feature, you can still use the standalone Docker image:

Example:

```
docker build -t pdf-letter-splitter .
docker run --rm \
  -v /path/to/input:/input \
  -v /path/to/output:/output \
  pdf-letter-splitter \
  /input/input.pdf /output
```

The container:

* Reads exactly one input PDF
* Writes all resulting PDFs into the output directory
* Uses heuristic-based filename extraction (no LLM normalization)

---

## Limitations

* This tool relies on heuristics and OCR
* Mis-splits or incorrect metadata can occur
* No review or correction workflow is included
* Best suited for scanned letters with reasonably standard layouts
* LLM normalization improves filename quality but is not perfect
* LLM requires a local model download (700 MB - 2.3 GB)

If higher accuracy is required, manual correction after the fact is expected.

---

## Configuration

### Environment Variables

- `LLAMA_SERVER_URL`: URL of the llama.cpp server (default: `http://localhost:8080`)
- `LLAMA_ENABLED`: Enable/disable LLM normalization (default: `false`, set to `true` in docker-compose)

### Disabling LLM

To disable LLM normalization:
```bash
docker-compose run --rm -e LLAMA_ENABLED=false pdf-splitter /input/file.pdf /output
```

Or use the standalone Docker image without docker-compose.

---

## Architecture

When using docker-compose:

1. **llama-server**: Runs llama.cpp with a GGUF model, provides HTTP API
2. **pdf-splitter**: Python service that:
   - Performs OCR on the input PDF
   - Detects letter boundaries
   - Extracts metadata using heuristics
   - Calls LLM server to normalize sender/topic (if enabled)
   - Falls back to heuristics if LLM fails
   - Generates output PDFs with clean filenames

Both services run offline once the model is downloaded.
