# pdf-letter-splitter

**Automatically split a scanned PDF with multiple letters into separate files—one PDF per letter.**

If you have a scanned document containing several letters (for example, from your mailbox), this tool will:
- Detect where each letter starts and ends
- Extract metadata like date, sender, and subject
- Create individual PDF files, one for each letter
- Name each file based on the extracted information

Perfect for organizing scanned correspondence without manual work.

---

## Quick Start

### Option 1: Use Pre-built Image from Docker Hub

**Bash:**
```bash
docker run --rm \
  -v /path/to/your/input:/input:ro \
  -v /path/to/your/output:/output \
  jasdefer/pdf-letter-splitter \
  -i /input/scanned-letters.pdf \
  --split-output /output
```

**PowerShell:**
```powershell
docker run --rm `
  -v C:\path\to\your\input:/input:ro `
  -v C:\path\to\your\output:/output `
  jasdefer/pdf-letter-splitter `
  -i /input/scanned-letters.pdf `
  --split-output /output
```

Replace `/path/to/your/input` with the folder containing your PDF, and `/path/to/your/output` with where you want the split files saved.

### Option 2: Build the Image Yourself

**Bash:**
```bash
cd Source
docker build -t pdf-letter-splitter .
docker run --rm \
  -v /path/to/your/input:/input:ro \
  -v /path/to/your/output:/output \
  pdf-letter-splitter \
  -i /input/scanned-letters.pdf \
  --split-output /output
```

**PowerShell:**
```powershell
cd Source
docker build -t pdf-letter-splitter .
docker run --rm `
  -v C:\path\to\your\input:/input:ro `
  -v C:\path\to\your\output:/output `
  pdf-letter-splitter `
  -i /input/scanned-letters.pdf `
  --split-output /output
```

---

## Command Line Parameters

All parameters are optional except `-i` (input file):

| Parameter | Description | Default |
|-----------|-------------|---------|
| `-i, --input` | **Required.** Path to input PDF file | None |
| `--split-output` | Directory where split PDF files will be saved | `letters` |
| `--verbose` | Show detailed processing information, debug logs, and save OCR data to `ocr_output.tsv` | Disabled |
| `--target-zip` | ZIP code to prioritize when multiple addresses are detected | None |
| `--single-page-only` | Treat every page as a separate one-page letter, bypassing split heuristics | Disabled |
| `--jobs N` | Number of parallel OCR jobs (0 = use all CPU cores) | `0` |
| `--no-rotate` | Disable automatic page rotation correction (rotation is on by default) | Rotation enabled |
| `--no-deskew` | Disable automatic page deskewing (deskewing is on by default) | Deskewing enabled |
| `--page-data` | Save page analysis data to JSON file (advanced usage) | None |

### Example with Parameters

**Bash:**
```bash
docker run --rm \
  -v /path/to/input:/input:ro \
  -v /path/to/output:/output \
  jasdefer/pdf-letter-splitter \
  -i /input/letters.pdf \
  --split-output /output \
  --verbose \
  --jobs 4
```

**PowerShell:**
```powershell
docker run --rm `
  -v C:\path\to\input:/input:ro `
  -v C:\path\to\output:/output `
  jasdefer/pdf-letter-splitter `
  -i /input/letters.pdf `
  --split-output /output `
  --verbose `
  --jobs 4
```

---

## How It Works

1. **OCR Processing**: The tool scans your PDF using OCR (Optical Character Recognition) to extract all text
2. **Language Support**: Recognizes German and English text automatically
3. **Letter Detection**: Analyzes the document structure to find where each letter begins and ends
4. **Metadata Extraction**: Identifies the date, sender, and subject from each letter's first page
5. **File Creation**: Saves each letter as a separate PDF with a descriptive filename

The entire process is fully automatic—no user interaction required.

---

## Output Files

### File Naming

Each output file is named based on extracted metadata:

**Complete metadata found:**
```
20241105-Finanzamt-Mahnung.pdf
20241220-Allianz-Versicherungspolice.pdf
```

Format: `YYYYMMDD-Sender-Topic.pdf`
- **Date**: `YYYYMMDD` format (e.g., `20241105` for November 5, 2024)
- **Sender**: Main word from sender's name
- **Topic**: Key words from subject line (up to 3 words)

**Missing metadata (incomplete):**
```
0_Incomplete_20241105-Finanzamt.pdf
0_Incomplete_Unknown.pdf
```

When date, sender, or subject cannot be extracted, files are prefixed with `0_Incomplete_`. This helps you quickly identify which letters need manual review.

**Duplicate names:**
```
20241105-Bank-Statement.pdf
20241105-Bank-Statement_1.pdf
20241105-Bank-Statement_2.pdf
```

If multiple letters would have the same filename, a number suffix is added automatically.

---

## OCR and Language Processing

**Supported Languages:**
- German (primary)
- English (secondary)

**OCR Features:**
- Automatic page rotation correction
- Automatic deskewing of tilted pages
- High-quality text extraction with position data
- Preserves original scan resolution (DPI)

**What Gets Extracted:**
- Date markers
- Sender information from letterheads
- Recipient addresses
- Subject lines
- Greetings and closings
- Page numbering (e.g., "Page 1 of 3")

---

## Processing Output and Logs

The tool logs all decisions to the console:

```
2026-01-23 14:23:10 - INFO - Processing 15 pages...
2026-01-23 14:23:45 - DEBUG - Split at Page 4 (Score: 1200)
2026-01-23 14:23:45 - INFO - Letter 1: Pages [1, 2, 3] (Date: 2024-11-05, Subject: Mahnung)
2026-01-23 14:23:45 - INFO - Created 20241105-Finanzamt-Mahnung.pdf (Pages: 1-3)
2026-01-23 14:23:46 - INFO - Letter 2: Pages [4, 5] (Date: N/A, Subject: N/A)
2026-01-23 14:23:46 - INFO - Created 0_Incomplete_Unknown.pdf (Pages: 4-5)
```

You'll see:
- How many pages were found
- Where letters were split
- What metadata was extracted
- Final output filenames

Use `--verbose` for detailed debug information.

---

## Known Limitations

**This tool uses heuristics and OCR—it will not be 100% accurate.**

**Common Issues:**

1. **Mis-splits**: May split one letter into multiple files or combine separate letters
2. **Metadata errors**: Dates, senders, or subjects may be wrong or missing
3. **Non-standard layouts**: Unusual letter formats may not be recognized correctly
4. **Poor scans**: Low quality, faded, or handwritten text reduces accuracy
5. **Language**: Only German and English are supported

**By Design:**

- No manual review or correction step
- No confidence scores or warnings
- Assumes standard Western business letter format
- Best effort only—manual verification recommended for important documents

**Recommendation:** Always review the output files, especially those marked `0_Incomplete_`.

---

## Advanced Usage

### Save OCR Data

When using the `--verbose` flag, OCR text with position data is automatically saved to `ocr_output.tsv` in the current directory. This file contains bounding box coordinates and confidence scores for all extracted text.

**Bash:**
```bash
docker run --rm -v /path/to/files:/work jasdefer/pdf-letter-splitter \
  -i /work/input.pdf --verbose
```

**PowerShell:**
```powershell
docker run --rm -v C:\path\to\files:/work jasdefer/pdf-letter-splitter `
  -i /work/input.pdf --verbose
```

### Save Page Analysis Data

Export page analysis results to JSON:

**Bash:**
```bash
docker run --rm -v /path/to/files:/work jasdefer/pdf-letter-splitter \
  -i /work/input.pdf --page-data /work/analysis.json
```

**PowerShell:**
```powershell
docker run --rm -v C:\path\to\files:/work jasdefer/pdf-letter-splitter `
  -i /work/input.pdf --page-data /work/analysis.json
```

---

## License

This project is licensed under the MIT License.

Copyright (c) 2026 Justus Bonz

See [LICENSE](LICENSE) file for details.
