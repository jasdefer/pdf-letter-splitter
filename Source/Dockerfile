# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /work

# Install system dependencies for OCR and PDF processing
RUN apt-get update && apt-get install -y \
    ocrmypdf \
    tesseract-ocr-deu \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Copy all Python scripts for the complete pipeline
COPY extract_text.py /app/extract_text.py
COPY analyze_letters.py /app/analyze_letters.py
COPY process_letters.py /app/process_letters.py

# Install Python dependencies
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org \
    pypdf

# Make scripts executable
RUN chmod +x /app/extract_text.py /app/analyze_letters.py /app/process_letters.py

# Add /app to PYTHONPATH so modules can import each other
ENV PYTHONPATH=/app:$PYTHONPATH

# Set the unified entry point as the entrypoint
ENTRYPOINT ["python3", "/app/process_letters.py"]

# Default command (can be overridden)
CMD []
