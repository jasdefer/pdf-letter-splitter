# LLM Models Directory

This directory should contain the GGUF model file for the llama.cpp server.

## Recommended Models

For German letter processing, we recommend using a small, efficient instruct model:

### Option 1: Llama 3.2 1B Instruct (Recommended)
- Model: `Llama-3.2-1B-Instruct-Q4_K_M.gguf`
- Size: ~700 MB
- Source: https://huggingface.co/lmstudio-community/Llama-3.2-1B-Instruct-GGUF
- Good balance of speed and quality

### Option 2: Phi-3 Mini Instruct
- Model: `Phi-3-mini-4k-instruct-q4.gguf`
- Size: ~2.3 GB
- Source: https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf
- Better quality, slightly slower

### Option 3: TinyLlama
- Model: `tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf`
- Size: ~650 MB
- Source: https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF
- Fastest, good for CPU-only

## Download Instructions

1. Choose a model from the options above
2. Download the GGUF file from HuggingFace
3. Place it in this directory
4. Rename it to `model.gguf` or update `docker-compose.yml` with the correct filename

Example using wget:
```bash
# For Llama 3.2 1B Instruct (recommended)
wget https://huggingface.co/lmstudio-community/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf -O model.gguf
```

Or using curl:
```bash
curl -L https://huggingface.co/lmstudio-community/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf -o model.gguf
```

## Requirements

- The model must be in GGUF format
- Recommend quantized models (Q4_K_M or Q5_K_M) for better performance
- Model should be instruction-tuned for best results
- File must be readable by the Docker container

## Offline Usage

Once downloaded, the model is stored locally and no internet connection is required at runtime.
