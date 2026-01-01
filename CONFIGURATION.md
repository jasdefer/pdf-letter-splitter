# Configuration Examples

## Basic Usage (with LLM)

Simple 2-step process - download model, then build:

```bash
# Step 1: Download model (one-time, ~650 MB)
./download-model.sh

# Step 2: Build with embedded model
docker-compose build

# Process PDFs (no additional setup needed)
mkdir -p input output
cp /path/to/your/scanned-letters.pdf input/
docker-compose run --rm pdf-splitter /input/scanned-letters.pdf /output

# Results will be in the output directory
ls output/
```

## CPU-Only Usage

The default `docker-compose.yml` is configured for CPU-only usage with an embedded model:

```bash
./download-model.sh      # Download model once
docker-compose build      # Build with embedded model
docker-compose run --rm pdf-splitter /input/letters.pdf /output
```

## GPU Usage (NVIDIA)

If you have an NVIDIA GPU with Docker GPU support:

```bash
# Download model once
./download-model.sh

# Build with GPU support
docker-compose -f docker-compose.gpu.yml build

# Use the GPU-enabled setup
docker-compose -f docker-compose.gpu.yml run --rm pdf-splitter /input/scanned-letters.pdf /output
```

## Without LLM (Fallback Mode)

If you don't want to download a model or use the LLM:

### Option 1: Disable LLM in docker-compose
```bash
docker-compose run --rm -e LLAMA_ENABLED=false pdf-splitter /input/scanned-letters.pdf /output
```

### Option 2: Use standalone Docker
```bash
docker build -t pdf-letter-splitter .
docker run --rm \
  -v $(pwd)/input:/input \
  -v $(pwd)/output:/output \
  pdf-letter-splitter /input/scanned-letters.pdf /output
```

## Advanced Configuration

### Using a Different Model

To use a different model:

```bash
# Download your preferred model
./download-model.sh llama32    # Better quality, ~700 MB
# or
./download-model.sh phi3        # Best quality, ~2.3 GB

# Rebuild to embed the new model
docker-compose build
```

See `models/README.md` for manual download options.

### Manual Model Download

If you prefer to download manually without the script:

```bash
# Download TinyLlama (recommended)
wget https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf -O model.gguf

# Then build
docker-compose build
```

### Adjust Context Size

To handle longer letters, edit `Dockerfile.llama` and change the `--n_ctx` parameter:

```dockerfile
CMD ["python", "-m", "llama_cpp.server", "--model", "/models/model.gguf", "--host", "0.0.0.0", "--port", "8080", "--n_ctx", "4096", "--n_gpu_layers", "0"]
```

Then rebuild: `docker-compose build`

### Environment Variables

You can override these in docker-compose or when running:

```bash
docker-compose run --rm \
  -e LLAMA_SERVER_URL=http://custom-server:8080 \
  -e LLAMA_ENABLED=true \
  pdf-splitter /input/file.pdf /output
```

## Troubleshooting

### Model File Not Found

Error: `model.gguf: No such file or directory` during build

Solution:
```bash
# Download the model first
./download-model.sh

# Then build
docker-compose build
```

### LLM Server Not Starting

Check logs:
```bash
docker-compose logs llama-server
```

Common issues:
- Model file missing: Run `./download-model.sh` before building
- Out of memory: Use a smaller model (TinyLlama) or increase Docker memory limit
- GPU not detected: Ensure NVIDIA Container Toolkit is installed

### Build Takes Long Time

The first build compiles llama-cpp-python which takes several minutes. This is normal. Subsequent builds are much faster (cached layers).

### Download Failed

If `./download-model.sh` fails:
1. Check your internet connection
2. Try manual download (see models/README.md)
3. If HuggingFace is blocked, use a mirror or VPN

### LLM Not Being Used

Check if it's enabled:
```bash
docker-compose run --rm pdf-splitter python3 -c "import os; print('LLAMA_ENABLED:', os.getenv('LLAMA_ENABLED', 'false'))"
```

### Slow Processing

- Use GPU if available (docker-compose.gpu.yml)
- Use a smaller model (TinyLlama)
- Increase CPU cores allocated to Docker
- Process fewer pages at once

### Bad Filename Quality

The LLM may not always produce perfect results. You can:
1. Try a better/larger model
2. Check the logs to see what the LLM returned
3. Fall back to heuristic mode if needed
4. Manually rename files after processing

## Performance Comparison

Typical processing times for a 10-page document:

| Configuration | Time | Filename Quality |
|--------------|------|------------------|
| Heuristic only | ~30s | Fair |
| LLM + CPU (TinyLlama) | ~45s | Good |
| LLM + CPU (Llama 3.2) | ~60s | Very Good |
| LLM + GPU (Llama 3.2) | ~35s | Very Good |

Times vary based on hardware and document complexity.
