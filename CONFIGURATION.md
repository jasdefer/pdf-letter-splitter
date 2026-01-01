# Configuration Examples

## Basic Usage (with LLM)

1. Download a model:
```bash
cd models
wget https://huggingface.co/lmstudio-community/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf -O model.gguf
cd ..
```

2. Process a PDF:
```bash
# Create input/output directories if they don't exist
mkdir -p input output

# Place your PDF in the input directory
cp /path/to/your/scanned-letters.pdf input/

# Run the splitter
docker-compose run --rm pdf-splitter /input/scanned-letters.pdf /output

# Results will be in the output directory
ls output/
```

## CPU-Only Usage

The default `docker-compose.yml` is configured for CPU-only usage. Just use it as shown above.

## GPU Usage (NVIDIA)

If you have an NVIDIA GPU with Docker GPU support:

```bash
# Use the GPU-enabled compose file
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

### Custom Model Path

Edit `docker-compose.yml` and change the model path:
```yaml
command: >
  --server
  --host 0.0.0.0
  --port 8080
  --model /models/your-custom-model.gguf
  --ctx-size 2048
  --n-gpu-layers 0
```

### Adjust Context Size

For longer letters, increase context size:
```yaml
command: >
  ...
  --ctx-size 4096
  ...
```

### GPU Layers (for GPU usage)

In `docker-compose.gpu.yml`, adjust `--n-gpu-layers`:
- `0`: CPU only
- `99`: Offload all layers to GPU (recommended)
- `1-98`: Partial GPU offloading

### Environment Variables

You can override these in docker-compose or when running:

```bash
docker-compose run --rm \
  -e LLAMA_SERVER_URL=http://custom-server:8080 \
  -e LLAMA_ENABLED=true \
  pdf-splitter /input/file.pdf /output
```

## Troubleshooting

### LLM Server Not Starting

Check logs:
```bash
docker-compose logs llama-server
```

Common issues:
- Model file not found: Ensure `models/model.gguf` exists
- Out of memory: Use a smaller model or increase Docker memory limit
- GPU not detected: Ensure NVIDIA Container Toolkit is installed

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
