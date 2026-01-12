# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /work

# Install system dependencies for OCR and PDF processing
RUN apt-get update && apt-get install -y \
    ocrmypdf \
    tesseract-ocr-deu \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org \
    -r /app/requirements.txt

# Copy the extraction script
COPY process_letters.py /app/process_letters.py

# Make script executable
RUN chmod +x /app/process_letters.py

# Set the script as the entrypoint
ENTRYPOINT ["python3", "/app/process_letters.py"]

# Default command (can be overridden)
CMD []
