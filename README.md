# pdf-letter-splitter

`pdf-letter-splitter` is a Dockerized tool that takes a **single scanned PDF containing multiple letters** and automatically splits it into **one PDF per letter**.

Each output PDF contains all pages belonging to exactly one letter and is named based on metadata extracted from the document using a **local LLM** (Large Language Model).

The tool is designed to be **best-effort, fully automatic, non-interactive, and completely offline** (no cloud services).

---

## What this tool does

* Accepts a scanned, multi-page PDF
* Runs OCR on the full document (German and English)
* Detects where one letter ends and the next begins using heuristics
* Extracts basic metadata from the first page of each letter **using a local LLM**:

  * Date
  * Sender
  * Topic
* Writes one PDF per detected letter

No manual review step or cloud services are included by design. All processing happens locally.

---

## Architecture

The tool uses a **two-container architecture**:

1. **llama.cpp server**: Runs a local LLM (GGUF format) for metadata extraction
2. **PDF splitter**: Performs OCR, boundary detection, and calls the LLM for metadata

Both containers run locally via Docker Compose, with optional GPU acceleration.

---

## Prerequisites

### Hardware

* **CPU mode**: Any modern CPU with 8GB+ RAM
* **GPU mode**: NVIDIA GPU with 8GB+ VRAM (recommended for faster inference)

### Software

* Docker and Docker Compose
* For GPU: NVIDIA Container Toolkit installed

---

## Getting Started

### Step 1: Download a GGUF model

You need to download a GGUF model file and place it in the `./models/` directory.

**Recommended models:**

1. **Qwen2.5-7B-Instruct (Q4_K_M quantization)** - Default, balanced quality/speed
   * Download from: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF
   * File: `qwen2.5-7b-instruct-q4_k_m.gguf` (~4.4 GB)
   * Good for: Most users, requires ~6GB VRAM

2. **Qwen2.5-7B-Instruct (Q5_K_M quantization)** - Higher quality
   * Download from: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF
   * File: `qwen2.5-7b-instruct-q5_k_m.gguf` (~5.3 GB)
   * Good for: Better accuracy, requires ~7GB VRAM

3. **Qwen2.5-3B-Instruct (Q4_K_M quantization)** - Faster, lower VRAM
   * Download from: https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF
   * File: `qwen2.5-3b-instruct-q4_k_m.gguf` (~2.0 GB)
   * Good for: Lower VRAM GPUs or faster processing

**Download instructions:**

```bash
# Create models directory
mkdir -p models

# Download using wget (example with Qwen2.5-7B Q4_K_M)
cd models
wget https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf

# Or download manually from the Hugging Face page and place in ./models/
```

**Important:** Update the `.env` file (copy from `.env.example`) to specify your model:

```bash
cp .env.example .env
# Edit .env and set LLAMA_ARG_MODEL to your downloaded model filename
```

Example `.env` content:

```
LLAMA_ARG_MODEL=/models/qwen2.5-7b-instruct-q4_k_m.gguf
```

### Step 2: Prepare your input

Create a `work` directory structure:

```bash
mkdir -p work/input work/output
```

Place your multi-letter PDF in `work/input/`:

```bash
cp your-scanned-letters.pdf work/input/input.pdf
```

### Step 3: Run with Docker Compose

**CPU mode:**

```bash
docker compose --profile cpu up
```

**GPU mode (NVIDIA GPU required):**

```bash
docker compose --profile gpu up
```

The process will:

1. Start the llama.cpp server and load the model
2. Wait for the server to be healthy
3. Run the PDF splitter
4. Output processed PDFs to `work/output/`
5. Exit automatically when done

### Step 4: Check your results

Find your split PDFs in `work/output/`:

```bash
ls -lh work/output/
```

Output files will be named based on extracted metadata:

* Fully recognized: `2024-11-05-Finanzamt-Mahnung.pdf`
* Unrecognized: `XXX-XXX-XXX-01.pdf`, `XXX-XXX-XXX-02.pdf`, etc.

---

## Configuration

### Environment Variables

You can customize behavior by editing `.env` or setting environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLAMA_ARG_MODEL` | `/models/Qwen2.5-7B-Instruct-Q4_K_M.gguf` | Path to GGUF model file (inside container) |
| `LLAMA_ARG_CTX_SIZE` | `4096` | Context window size in tokens |
| `LLAMA_ARG_N_GPU_LAYERS` | `999` (GPU) / `0` (CPU) | Number of layers to offload to GPU |
| `LLAMA_BASE_URL` | `http://llama-server:8080` | URL of the LLM server |
| `MODEL_FIELDS_LANGUAGE_HINT` | `deu+eng` | Language hint for prompts (German + English) |
| `INPUT_PDF` | `/work/input/input.pdf` | Input PDF path (inside container) |
| `OUTPUT_DIR` | `/work/output` | Output directory (inside container) |
| `LLM_TEMPERATURE` | `0.1` | LLM temperature (lower = more deterministic) |
| `LLM_MAX_TOKENS` | `256` | Maximum tokens for LLM response |

See `.env.example` for more details.

---

## Advanced Usage

### Using a different model

1. Download any GGUF model (e.g., from Hugging Face)
2. Place it in `./models/`
3. Update `LLAMA_ARG_MODEL` in `.env`
4. Adjust `LLAMA_ARG_CTX_SIZE` and `LLAMA_ARG_N_GPU_LAYERS` if needed

### Processing multiple PDFs

To process multiple PDFs, run the splitter service for each file:

```bash
# Process first PDF
INPUT_PDF=/work/input/file1.pdf docker compose --profile cpu run --rm splitter

# Process second PDF
INPUT_PDF=/work/input/file2.pdf docker compose --profile cpu run --rm splitter
```

### Standalone LLM server

You can keep the LLM server running and process PDFs separately:

```bash
# Start only the LLM server
docker compose --profile cpu up -d llama-server

# Process PDFs as needed
docker compose --profile cpu run --rm splitter

# Stop the server when done
docker compose down
```

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
* Extracted metadata per letter (via LLM)
* Final output filenames
* LLM interactions and any fallback to default values

No manifest or sidecar files are generated.

---

## Limitations

* This tool relies on heuristics, OCR, and LLM inference
* Mis-splits or incorrect metadata can occur
* LLM responses may vary slightly between runs (though low temperature improves consistency)
* No review or correction workflow is included
* Best suited for scanned letters with reasonably standard layouts
* Requires downloading a 2-5GB model file

If higher accuracy is required, manual correction after the fact is expected.

---

## Troubleshooting

### LLM server doesn't start

* Check that the model file exists in `./models/` and matches the path in `.env`
* Verify you have enough RAM/VRAM for the model
* For GPU: Ensure NVIDIA Container Toolkit is installed

### Metadata extraction fails (all XXX)

* Check that the llama-server is running and healthy: `docker compose logs llama-server`
* Verify network connectivity between containers
* Check splitter logs: `docker compose logs splitter`
* Try increasing `LLM_TIMEOUT` in `.env` if requests time out

### GPU not being used

* Ensure you're using `--profile gpu` (not `cpu`)
* Verify NVIDIA Container Toolkit is installed: `docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi`
* Check GPU availability in container: `docker compose --profile gpu exec llama-server-gpu nvidia-smi`

---

## Migration from regex-based version

If you were using an older version with regex-based metadata extraction:

* The OCR and boundary detection logic remains unchanged
* Only metadata extraction now uses the LLM
* You'll need to set up the LLM server (see Getting Started)
* Output format and naming conventions are identical
* The tool is now fully offline/local (no external APIs)
