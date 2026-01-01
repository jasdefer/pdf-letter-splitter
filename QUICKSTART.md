# Quick Start Guide

Get started with LLM-enhanced PDF letter splitting in 2 simple steps:

## Step 1: Download Model & Build

```bash
# Download the model (~650 MB, one-time setup)
./download-model.sh

# Build the Docker images (embeds the model)
docker-compose build
```

**That's it!** The model is now embedded in the Docker image. No manual files to manage.

## Step 2: Process Your PDFs

```bash
# Create directories (if they don't exist)
mkdir -p input output

# Copy your scanned PDF to input
cp /path/to/your/letters.pdf input/

# Process with LLM normalization
docker-compose run --rm pdf-splitter /input/letters.pdf /output
```

## Results

Your split PDFs appear in `output/` with clean names like:

```
2024-11-05-Deutsche-Bank-Kontoauszug.pdf
2024-11-10-Finanzamt-München-Steuerbescheid.pdf
2024-11-15-Versicherung-Beitragsrechnung.pdf
```

## GPU Support (Optional)

If you have an NVIDIA GPU:

```bash
# Download model
./download-model.sh

# Build with GPU support
docker-compose -f docker-compose.gpu.yml build

# Process with GPU acceleration
docker-compose -f docker-compose.gpu.yml run --rm pdf-splitter /input/letters.pdf /output
```

## Using a Different Model

```bash
# Choose a model: tinyllama (default), llama32 (better), phi3 (best)
./download-model.sh llama32

# Rebuild to embed the new model
docker-compose build
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
