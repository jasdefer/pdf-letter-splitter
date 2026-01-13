#!/usr/bin/env python3
"""
OCR-based text extractor for PDF documents with positional data.

Extracts text from each page of a PDF using OCRmyPDF with Tesseract TSV output,
providing bounding box coordinates for downstream processing.
"""

import argparse
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

try:
    import pandas as pd
    import pytesseract
    from PIL import Image
except ImportError as e:
    print(f"Error: Required package not found: {e}", file=sys.stderr)
    print("Install with: pip install pandas pytesseract Pillow", file=sys.stderr)
    sys.exit(1)

# Set up module-level logger
logger = logging.getLogger(__name__)


def extract_text(input_path: Path, lang: str = 'deu+eng', 
                rotate: bool = True, deskew: bool = True, 
                jobs: int = 0) -> pd.DataFrame:
    """
    Extract text with positional data from all pages of a PDF using OCR.
    
    Uses ocrmypdf to preprocess the PDF (rotation, deskewing), then uses
    Tesseract to extract text in TSV format with bounding box coordinates.
    
    Args:
        input_path: Path to input PDF file
        lang: Tesseract language codes (default: 'deu+eng')
        rotate: Enable automatic page rotation correction (default: True)
        deskew: Enable deskewing of pages (default: True)
        jobs: Number of parallel jobs (0 = use all CPU cores, default: 0)
        
    Returns:
        pandas DataFrame with columns:
            - level: OCR hierarchy level (1=page, 2=block, 3=paragraph, 4=line, 5=word)
            - page_num: Page number (1-indexed)
            - block_num: Block number within page
            - par_num: Paragraph number within block
            - line_num: Line number within paragraph
            - word_num: Word number within line
            - left: Left coordinate (pixels)
            - top: Top coordinate (pixels)
            - width: Width (pixels)
            - height: Height (pixels)
            - conf: Confidence score (-1 for non-leaf elements)
            - text: Extracted text
            - right: Right coordinate (pixels) = left + width
            - bottom: Bottom coordinate (pixels) = top + height
            - page_width: Page width in pixels
            - page_height: Page height in pixels
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        RuntimeError: For OCR processing errors
        ValueError: For invalid PDF files
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    if not input_path.is_file():
        raise ValueError(f"Input path is not a file: {input_path}")
    
    logger.info(f"Processing PDF: {input_path}")
    
    # Create a temporary file for the OCR'd PDF
    temp_fd, temp_ocr_pdf = tempfile.mkstemp(suffix='.pdf')
    os.close(temp_fd)
    
    try:
        # Run ocrmypdf to preprocess the PDF (rotation, deskewing)
        logger.info("Running OCRmyPDF preprocessing...")
        ocrmypdf_cmd = [
            'ocrmypdf',
            '--language', lang,
            '--force-ocr',  # Always use OCR, never rely on embedded text
            '--output-type', 'pdf',
            '--pdf-renderer', 'sandwich',
            '--jobs', str(jobs),
        ]
        
        # Add optional rotation correction
        if rotate:
            ocrmypdf_cmd.append('--rotate-pages')
        
        # Add optional deskewing
        if deskew:
            ocrmypdf_cmd.append('--deskew')
        
        # Add input and output paths
        ocrmypdf_cmd.extend([str(input_path), temp_ocr_pdf])
        
        result = subprocess.run(ocrmypdf_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else result.stdout
            raise RuntimeError(f"OCR processing failed: {error_msg}")
        
        logger.info("OCRmyPDF preprocessing completed successfully")
        
        # Now extract TSV data using Tesseract directly
        logger.info("Extracting TSV data with Tesseract...")
        
        # We need to convert PDF pages to images and run Tesseract on each
        # Use pdf2image or similar, but to keep dependencies minimal,
        # we can use ocrmypdf output and extract images using pypdf
        # However, the issue says to avoid pypdf for text extraction
        # Let's use a different approach: convert PDF to images using pdftoppm
        
        all_dataframes = []
        
        # Get page count from the PDF
        page_count = _get_pdf_page_count(temp_ocr_pdf)
        logger.info(f"Processing {page_count} pages...")
        
        for page_num in range(1, page_count + 1):
            logger.debug(f"Processing page {page_num}/{page_count}")
            
            # Convert page to image
            with tempfile.TemporaryDirectory() as tmpdir:
                # Use pdftoppm to convert page to image
                image_path = Path(tmpdir) / f"page_{page_num}.png"
                pdftoppm_cmd = [
                    'pdftoppm',
                    '-png',
                    '-f', str(page_num),
                    '-l', str(page_num),
                    '-singlefile',
                    temp_ocr_pdf,
                    str(image_path.with_suffix(''))
                ]
                
                result = subprocess.run(pdftoppm_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise RuntimeError(f"Failed to convert page {page_num} to image: {result.stderr}")
                
                # Run Tesseract on the image to get TSV
                image = Image.open(image_path)
                page_width, page_height = image.size
                
                tsv_string = pytesseract.image_to_data(
                    image,
                    lang=lang,
                    output_type=pytesseract.Output.DATAFRAME
                )
                
                # pytesseract returns a DataFrame when using Output.DATAFRAME
                df = tsv_string
                
                # Add page_num column (Tesseract uses page_num=0 for single images)
                df['page_num'] = page_num
                
                # Add derived columns
                df['right'] = df['left'] + df['width']
                df['bottom'] = df['top'] + df['height']
                df['page_width'] = page_width
                df['page_height'] = page_height
                
                all_dataframes.append(df)
        
        # Combine all pages
        if all_dataframes:
            result_df = pd.concat(all_dataframes, ignore_index=True)
            logger.info(f"Extracted {len(result_df)} OCR elements across {page_count} pages")
            return result_df
        else:
            raise ValueError("No pages found in PDF")
        
    finally:
        # Clean up temporary file
        if os.path.exists(temp_ocr_pdf):
            os.unlink(temp_ocr_pdf)


def _get_pdf_page_count(pdf_path: str) -> int:
    """
    Get the number of pages in a PDF using pdfinfo.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Number of pages
    """
    result = subprocess.run(
        ['pdfinfo', pdf_path],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get PDF info: {result.stderr}")
    
    for line in result.stdout.split('\n'):
        if line.startswith('Pages:'):
            return int(line.split(':')[1].strip())
    
    raise RuntimeError("Could not determine page count from pdfinfo output")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Extract text with positional data from PDF using OCR (German + English)'
    )
    parser.add_argument(
        '-i', '--input',
        type=str,
        default='input.pdf',
        help='Input PDF file path (default: input.pdf)'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='output.tsv',
        help='Output TSV file path (default: output.tsv)'
    )
    parser.add_argument(
        '--no-rotate',
        action='store_true',
        help='Disable automatic page rotation correction'
    )
    parser.add_argument(
        '--no-deskew',
        action='store_true',
        help='Disable deskewing of pages'
    )
    parser.add_argument(
        '--jobs',
        type=int,
        default=0,
        help='Number of parallel OCR jobs (0 = use all CPU cores, default: 0)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose debug logging and dump OCR output to ocr_output.tsv'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    try:
        # Extract text from PDF
        logger.info("Starting OCR extraction...")
        result_df = extract_text(
            input_path,
            rotate=not args.no_rotate,
            deskew=not args.no_deskew,
            jobs=args.jobs
        )
        
        # If verbose, also dump to ocr_output.tsv
        if args.verbose:
            verbose_output_path = Path('ocr_output.tsv')
            logger.debug(f"Dumping full OCR table to {verbose_output_path}")
            result_df.to_csv(verbose_output_path, sep='\t', index=False)
        
        logger.info(f"Successfully extracted text from {result_df['page_num'].nunique()} pages")
        logger.info(f"Total OCR elements: {len(result_df)}")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=args.verbose)
        sys.exit(1)


if __name__ == '__main__':
    main()
