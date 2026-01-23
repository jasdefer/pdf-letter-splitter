# pdf-letter-splitter

A Dockerized tool that automatically splits a scanned PDF containing multiple letters into separate PDF files—one per letter.

## What this tool does

Takes a single scanned PDF with multiple letters and:

* Runs OCR (German + English) on all pages
* Detects where each letter begins and ends
* Extracts metadata (date, sender, subject) from each letter's first page
* Outputs one PDF file per letter

Fully automatic with no manual intervention required.

---

## Input and Output

**Input:**
* A scanned multi-page PDF file
* Can be rotated, skewed, or contain multiple separate letters

**Output:**
* One PDF file per detected letter
* All output files written to a single output directory
* Filenames based on extracted metadata

---

## Output Filename Rules

Filenames are constructed from extracted metadata:

### Fully recognized letters

When date, sender, and subject are all successfully extracted:

```
YYYYMMDD-Sender-Topic.pdf
```

Example:
```
20241105-Finanzamt-Mahnung.pdf
```

**Rules:**
* Date format: `YYYYMMDD` (no separators)
* Sender: Longest word from sender name, special characters removed
* Topic: Up to 3 significant words (stop words filtered), concatenated without spaces
* Fully recognized files do not get a numeric suffix

### Partially recognized letters

When **any** field (date, sender, or subject) is missing:

```
0_Incomplete_YYYYMMDD-Sender-Topic.pdf
```

Example:
```
0_Incomplete_20241105-Finanzamt.pdf
0_Incomplete_Allianz-Invoice.pdf
```

**Rules:**
* Files are prefixed with `0_Incomplete_` to indicate missing metadata
* Available metadata is still included in the filename
* If all metadata is missing: `0_Incomplete_Unknown.pdf`

### Filename collisions

If multiple letters would have identical filenames:

```
20241105-Allianz-Invoice.pdf
20241105-Allianz-Invoice_1.pdf
20241105-Allianz-Invoice_2.pdf
```

A numeric suffix `_1`, `_2`, etc. is appended automatically.

---

## OCR and Language Handling

**Languages:**
* German (primary)
* English (secondary)
* Both languages processed simultaneously

**OCR behavior:**
* Applied once to the entire input PDF
* Uses Tesseract via OCRmyPDF
* Automatic page rotation and deskewing
* Original DPI preserved in output files

**Text extraction:**
* Positional data captured (bounding boxes for all text)
* Used to detect document structure markers (addresses, dates, greetings, etc.)

---

## Logging Behavior

All processing decisions are logged to standard output:

* Number of pages detected in input PDF
* Page-by-page split decisions with scores
* Detected document markers (page indices, addresses, subjects, greetings)
* Extracted metadata for each letter (date, sender, subject)
* Output filenames and page ranges for each letter

Example log output:

```
2026-01-23 14:23:10 - INFO - Processing 15 pages...
2026-01-23 14:23:45 - DEBUG - Split at Page 4 (Score: 1200). Factors: New Index (+1000), Address Block at top (+450)
2026-01-23 14:23:45 - INFO - Letter 1: Pages [1, 2, 3] (Date: 2024-11-05, Subject: Mahnung)
2026-01-23 14:23:45 - INFO - Created 20241105-Finanzamt-Mahnung.pdf (Pages: 1-3)
```

No separate manifest or metadata files are generated.

---

## Docker Usage

### Build the image

```bash
cd Source
docker build -t pdf-letter-splitter .
```

### Run the splitter

```bash
docker run --rm \
  -v /path/to/input:/input:ro \
  -v /path/to/output:/output \
  pdf-letter-splitter \
  -i /input/letters.pdf \
  --split-output /output
```

**Arguments:**
* `-i, --input`: Path to input PDF file
* `--split-output`: Directory for split PDF output files
* `--verbose`: Enable detailed debug logging
* `--target-zip`: ZIP code to prioritize when multiple addresses found
* `--jobs N`: Number of parallel OCR jobs (0 = use all CPU cores)
* `--no-rotate`: Disable automatic page rotation correction
* `--no-deskew`: Disable page deskewing

---

## Known Limitations

**Expected failure modes:**

* **Mis-splits**: The tool may split a single letter into multiple files, or combine multiple letters into one file
* **Metadata extraction errors**: Dates, senders, or subjects may be incorrectly extracted or missed entirely
* **Non-standard layouts**: Letters with unusual formatting may not be detected correctly
* **Low-quality scans**: Poor scan quality reduces OCR accuracy and increases errors

**By design:**

* No manual review or correction workflow
* No confidence scores or warnings for uncertain splits
* No support for languages other than German and English
* Assumes Western-style letter format (address block, date, subject, greeting, body, closing)

**This is a heuristic-based tool.** Manual review and correction of output is expected when accuracy is critical.

---

## License

This project is licensed under the MIT License.

Copyright (c) 2026 Justus Bonz

See [LICENSE](LICENSE) file for full license text.
