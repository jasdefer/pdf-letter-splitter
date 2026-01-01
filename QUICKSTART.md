# Quick Start Guide

Get started with LLM-enhanced PDF letter splitting in 3 steps:

## Step 1: Download a Model (One-Time Setup)

```bash
cd models
wget https://huggingface.co/lmstudio-community/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf -O model.gguf
cd ..
```

**Alternative models**: See `models/README.md` for other options.

## Step 2: Prepare Your Files

```bash
# Create directories (if they don't exist)
mkdir -p input output

# Copy your scanned PDF to input
cp /path/to/your/letters.pdf input/
```

## Step 3: Process

### With LLM (Recommended)

```bash
# CPU-only
docker-compose run --rm pdf-splitter /input/letters.pdf /output

# With GPU (if available)
docker-compose -f docker-compose.gpu.yml run --rm pdf-splitter /input/letters.pdf /output
```

### Without LLM

```bash
# Disable LLM, use heuristics only
docker-compose run --rm -e LLAMA_ENABLED=false pdf-splitter /input/letters.pdf /output
```

## Results

Your split PDFs will appear in `output/` with clean names like:

```
2024-11-05-Deutsche-Bank-Kontoauszug.pdf
2024-11-10-Finanzamt-München-Steuerbescheid.pdf
2024-11-15-Versicherung-Beitragsrechnung.pdf
```

## Troubleshooting

- **Model not found**: Ensure `models/model.gguf` exists
- **LLM server won't start**: Check logs with `docker-compose logs llama-server`
- **Slow processing**: Try a smaller model (TinyLlama) or use GPU
- **Bad filenames**: Check logs, increase context, or use fallback mode

For more details, see:
- `CONFIGURATION.md` - Advanced usage and configuration
- `README.md` - Full documentation
- `IMPLEMENTATION_SUMMARY.md` - Technical details
