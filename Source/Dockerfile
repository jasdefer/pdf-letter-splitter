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

# Copy the extraction scripts
COPY extract_text.py /app/extract_text.py
COPY detect_boundaries.py /app/detect_boundaries.py

# Install Python dependencies
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org \
    pypdf \
    requests

# Make script executable
RUN chmod +x /app/extract_text.py

# Add /app to PYTHONPATH so detect_boundaries can be imported
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Set the script as the entrypoint
ENTRYPOINT ["python3", "/app/extract_text.py"]

# Default command (can be overridden)
CMD []
