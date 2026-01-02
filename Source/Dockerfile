# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /work

# Install system dependencies for OCR and PDF processing
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-deu \
    tesseract-ocr-eng \
    poppler-utils \
    ghostscript \
    qpdf \
    mupdf-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy the extraction script
COPY extract_text.py /app/extract_text.py

# Install Python dependencies
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org \
    pdf2image \
    pytesseract \
    pillow

# Make script executable
RUN chmod +x /app/extract_text.py

# Set the script as the entrypoint
ENTRYPOINT ["python3", "/app/extract_text.py"]

# Default command (can be overridden)
CMD []
