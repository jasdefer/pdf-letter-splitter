# Dockerfile for pdf-letter-splitter
# Provides a complete environment for OCR-based PDF letter splitting

FROM python:3.11-slim

# Install system dependencies
# - tesseract-ocr: OCR engine
# - tesseract-ocr-deu: German language pack
# - tesseract-ocr-eng: English language pack
# - poppler-utils: PDF utilities (pdftotext, pdfinfo)
# - qpdf: PDF manipulation tool
# - ghostscript: PostScript and PDF interpreter (required by ocrmypdf)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-deu \
    tesseract-ocr-eng \
    poppler-utils \
    qpdf \
    ghostscript \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies for OCR and PDF processing
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org \
    ocrmypdf \
    pypdf

# Create working directories
RUN mkdir -p /input /output

# Copy the processing script
COPY process_pdf.py /usr/local/bin/process_pdf.py
RUN chmod +x /usr/local/bin/process_pdf.py

# Set the working directory
WORKDIR /work

# Set the entrypoint to run the processing script
ENTRYPOINT ["python3", "/usr/local/bin/process_pdf.py"]
