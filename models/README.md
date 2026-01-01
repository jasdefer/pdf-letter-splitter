# LLM Models Directory

**Note: The model is now embedded directly in the Docker image. You download it once, then build - no manual setup needed at runtime!**

## Quick Setup

Use the provided download script:

```bash
# Download the default model (TinyLlama, ~650 MB)
./download-model.sh

# Or choose a specific model:
./download-model.sh tinyllama   # Fastest, ~650 MB
./download-model.sh llama32     # Better quality, ~700 MB
./download-model.sh phi3        # Best quality, ~2.3 GB
```

Then build:
```bash
docker-compose build
```

The model is now embedded in the Docker image - no external files needed!

## Manual Download

If you prefer to download manually:

### TinyLlama (Recommended - Fast & Small)
```bash
wget https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf -O model.gguf
```

### Llama 3.2 1B (Better Quality)
```bash
wget https://huggingface.co/lmstudio-community/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf -O model.gguf
```

### Phi-3 Mini (Best Quality)
```bash
# Note: This is a larger download (~2.3 GB)
wget https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf -O model.gguf
```

## How It Works

1. The `model.gguf` file is copied into the Docker image during build
2. The llama-server starts with the embedded model
3. No external files or mounts needed at runtime
4. The model persists in the image - download once, use anywhere

## Changing Models

To use a different model:

1. Delete the old model: `rm model.gguf`
2. Download a new one (using the script or manually)
3. Rebuild: `docker-compose build`

## Offline Usage

After building the image with an embedded model:
- No internet connection required at runtime
- No external model files needed
- The container is fully self-contained
