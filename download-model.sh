#!/bin/bash
# download-model.sh - Helper script to download a GGUF model for the llama-server
#
# Usage:
#   ./download-model.sh [model-choice]
#
# Model choices:
#   tinyllama (default) - TinyLlama 1.1B (~650 MB, fastest)
#   llama32          - Llama 3.2 1B (~700 MB, better quality)
#   phi3             - Phi-3 Mini (~2.3 GB, best quality)

set -e

# Default model
MODEL_CHOICE="${1:-tinyllama}"

# Model URLs
case "$MODEL_CHOICE" in
    tinyllama)
        MODEL_URL="https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
        MODEL_NAME="TinyLlama 1.1B Chat"
        MODEL_SIZE="~650 MB"
        ;;
    llama32)
        MODEL_URL="https://huggingface.co/lmstudio-community/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf"
        MODEL_NAME="Llama 3.2 1B Instruct"
        MODEL_SIZE="~700 MB"
        ;;
    phi3)
        MODEL_URL="https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
        MODEL_NAME="Phi-3 Mini 4K Instruct"
        MODEL_SIZE="~2.3 GB"
        ;;
    *)
        echo "Error: Unknown model choice '$MODEL_CHOICE'"
        echo "Available models: tinyllama, llama32, phi3"
        exit 1
        ;;
esac

echo "=========================================="
echo "Downloading model for llama-server"
echo "=========================================="
echo "Model: $MODEL_NAME"
echo "Size: $MODEL_SIZE"
echo "Target: ./model.gguf"
echo ""

# Check if model.gguf already exists
if [ -f "model.gguf" ]; then
    echo "Warning: model.gguf already exists!"
    read -p "Do you want to replace it? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Download cancelled."
        exit 0
    fi
    rm model.gguf
fi

# Download model
echo "Downloading... (this may take several minutes)"
if command -v wget > /dev/null; then
    wget -O model.gguf "$MODEL_URL" --progress=bar:force 2>&1
elif command -v curl > /dev/null; then
    curl -L "$MODEL_URL" -o model.gguf --progress-bar
else
    echo "Error: Neither wget nor curl is available"
    exit 1
fi

# Verify download
if [ -f "model.gguf" ] && [ -s "model.gguf" ]; then
    FILE_SIZE=$(du -h model.gguf | cut -f1)
    echo ""
    echo "=========================================="
    echo "Download complete!"
    echo "=========================================="
    echo "File: model.gguf"
    echo "Size: $FILE_SIZE"
    echo ""
    echo "Next steps:"
    echo "1. Build the Docker image:"
    echo "   docker-compose build"
    echo ""
    echo "2. Run the PDF splitter:"
    echo "   docker-compose run --rm pdf-splitter /input/file.pdf /output"
else
    echo "Error: Download failed or file is empty"
    exit 1
fi
