# Page Data Structure and Marker Detection

This directory contains the core data structures and detection pipeline for analyzing OCR-processed PDF pages.

## Overview

The page data module provides a stable, strongly-typed per-page data structure that represents all information about one scanned page of a PDF document. This structure serves as the central container for page-level signals and extracted facts.

## Architecture

### Core Modules

#### `page_data.py`
Defines the core data structures:
- **`PageData`**: Main structure representing one scanned page with all detected markers
- **`PageInfoDetected`**: Represents page numbering information (e.g., "Seite 2 von 4")
- **`TextMarker`**: Generic marker for text-based signals (greetings, closings, subjects, etc.)

All structures support JSON serialization for debugging and inspection.

#### `marker_detection.py`
Contains detection functions that analyze page content:
- `detect_page_info(page_df)`: Detects page numbering
- `detect_greeting(page_df)`: Detects greeting markers
- `detect_goodbye(page_df)`: Detects closing/goodbye markers
- `detect_betreff(page_df)`: Detects subject lines
- `detect_address_block(page_df)`: Detects address blocks

**Note**: Current implementations are stubs that return `found=False`. Actual detection logic will be added in follow-up issues.

#### `page_analysis.py`
Provides orchestration:
- `analyze_pages(ocr_df)`: Main entry point that processes all pages and returns a list of `PageData` instances

## Usage Example

```python
from process_letters import extract_text
from page_analysis import analyze_pages
from page_data import page_data_list_to_json

# Step 1: Extract OCR data from PDF
ocr_df = extract_text(Path("document.pdf"))

# Step 2: Analyze pages
pages = analyze_pages(ocr_df)

# Step 3: Access detected information
for page in pages:
    print(f"Page {page.scan_page_num}:")
    print(f"  Greeting found: {page.greeting.found}")
    print(f"  Page info: {page.page_info.current}/{page.page_info.total}")

# Step 4: Export to JSON
json_output = page_data_list_to_json(pages)
```

## Data Flow

```
PDF Document
    ↓
[extract_text] (process_letters.py)
    ↓
OCR DataFrame (pandas)
    ↓
[analyze_pages] (page_analysis.py)
    ↓
List[PageData] (one per page)
    ↓
[page_data_list_to_json]
    ↓
JSON output for inspection
```

## Testing

Run the test suite:
```bash
python3 -m unittest Test.test_page_data -v
```

Run only unit tests (without OCR integration):
```bash
python3 -m unittest Test.test_page_data.TestPageDataStructures \
                     Test.test_page_data.TestMarkerDetection \
                     Test.test_page_data.TestPageAnalysis -v
```

See the demonstration script:
```bash
python3 Test/demo_page_analysis.py
```

## Extending Detection

To add a new marker:

1. Add a field to `PageData` in `page_data.py`:
   ```python
   @dataclass
   class PageData:
       # ... existing fields ...
       new_marker: TextMarker
   ```

2. Add a detection function in `marker_detection.py`:
   ```python
   def detect_new_marker(page_df: pd.DataFrame) -> TextMarker:
       # Your detection logic here
       return TextMarker(found=True, raw="...", text="...")
   ```

3. Wire it into `analyze_pages` in `page_analysis.py`:
   ```python
   page_data = PageData(
       # ... existing fields ...
       new_marker=detect_new_marker(page_df)
   )
   ```

4. Update `PageData.from_dict()` if needed for deserialization.

## Design Principles

- **One PageData per scanned page**: Each structure represents exactly one page
- **Strongly typed**: Use dataclasses with type hints
- **Stable contract**: Downstream logic depends only on PageData, not OCR internals
- **Easy to extend**: Adding new markers requires minimal changes
- **JSON serializable**: All structures can be exported for debugging
- **No detection logic in structures**: Keep data and detection separate

## Future Work

- Implement actual detection heuristics in `marker_detection.py`
- Add confidence scores to markers
- Add positional information (bounding boxes)
- Support for multi-language detection
- Performance optimizations for large documents
