# pdf-letter-splitter

`pdf-letter-splitter` is a Dockerized tool that takes a **single scanned PDF containing multiple letters** and automatically splits it into **one PDF per letter**.

Each output PDF contains all pages belonging to exactly one letter and is named based on metadata extracted from the document.

The tool is designed to be **best-effort, fully automatic, and non-interactive**.

---

## What this tool does

* Accepts a scanned, multi-page PDF
* Runs OCR on the full document (German and English)
* Detects where one letter ends and the next begins
* Extracts basic metadata from the first page of each letter:

  * Date
  * Sender
  * Topic
* Writes one PDF per detected letter

No manual review step is included by design.

---

## Output naming

Each output file is written to a flat output directory.

### Fully recognized letters

If all fields are successfully extracted:

```
YYYY-MM-DD-Sender-Topic.pdf
```

Example:

```
2024-11-05-Finanzamt-Mahnung.pdf
```

### Partially or unrecognized letters

If **any** of the fields (date, sender, topic) cannot be extracted:

```
XXX-XXX-XXX-01.pdf
XXX-XXX-XXX-02.pdf
...
```

Rules:

* `XXX` is always used for missing or unreliable metadata
* The numeric suffix is incremented **only** for these unrecognized files
* Fully recognized files never receive a suffix

---

## Language and OCR behavior

* OCR is applied to the entire input PDF once
* Supported languages:

  * German
  * English
* Language detection is automatic
* German is preferred when ambiguity exists
* The input PDF’s resolution (DPI) is preserved

---

## Logging and transparency

All processing decisions are written to standard output, including:

* Detected letter start pages
* Heuristics that triggered splits
* Extracted metadata per letter
* Final output filenames

No manifest or sidecar files are generated.

---

## Usage (Docker)

Example:

```
docker run --rm \
  -v /path/to/input:/input \
  -v /path/to/output:/output \
  pdf-letter-splitter \
  /input/input.pdf /output
```

The container:

* Reads exactly one input PDF
* Writes all resulting PDFs into the output directory

---

## Limitations

* This tool relies on heuristics and OCR
* Mis-splits or incorrect metadata can occur
* No review or correction workflow is included
* Best suited for scanned letters with reasonably standard layouts

If higher accuracy is required, manual correction after the fact is expected.

---

## OCR Text Extractor

This repository also includes a standalone OCR text extraction tool located in the `Source/` directory.

The extractor provides:

* Per-page text extraction from scanned PDFs
* OCR with German and English language support
* JSON output format
* Automatic PDF repair for corrupted documents
* Docker-based deployment

See [`Source/README.md`](Source/README.md) for detailed usage instructions.

Quick example:

```bash
docker build -t pdf-letter-splitter Source/
docker run --rm -v "$(pwd):/work" pdf-letter-splitter \
  -i Test/test.pdf -o output.json
```
