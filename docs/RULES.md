# KDP paperback rule snapshot

Profile: `kdp-paperback`  
Snapshot: `2026-07-30`

ProofMill keeps rule sources visible because platform requirements can change. The main
primary sources are:

- [Paperback submission guidelines](https://kdp.amazon.com/en_US/help/topic/G201857950)
- [Trim size, bleed, and margins](https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6)
- [Paperback fonts](https://kdp.amazon.com/en_US/help/topic/G202145450)
- [Book image guidance](https://kdp.amazon.com/en_US/help/topic/G202169030)
- [Formatting issue repairs](https://kdp.amazon.com/en_US/help/topic/G201834260)

Run `proofmill rules --json` to obtain the machine-readable registry bundled with the
installed version.

## Blocking errors

| Code | Trigger |
| --- | --- |
| `PDF_ENCRYPTED` | input requires a password or carries encryption |
| `PDF_PARSE_ERROR` | parser cannot read the document structure |
| `FILE_TOO_LARGE` | file is larger than 650 MB |
| `PAGE_COUNT_OUT_OF_RANGE` | selected ink/paper range does not contain the PDF page count |
| `PAGE_SIZE_MISMATCH` | a page differs from expected trim plus selected bleed by more than 1 pt |
| `PAGE_SIZE_INCONSISTENT` | the interior contains multiple page dimensions |
| `SPREAD_DETECTED` | a page is approximately double the expected single-page width |
| `FONT_NOT_EMBEDDED` | text uses a PDF font resource without an embedded font program |
| `TEXT_OUTSIDE_SAFE_AREA` | a word box crosses the mirrored inside/outside safe rectangle |
| `IMAGE_LOW_DPI` | effective horizontal or vertical placed-image DPI is below 300 |
| `ANNOTATIONS_PRESENT` | a page contains PDF annotations, including link annotations |
| `FORM_FIELDS_PRESENT` | the catalog contains AcroForm fields |
| `JAVASCRIPT_PRESENT` | the catalog contains a JavaScript name tree or open action |
| `ATTACHMENTS_PRESENT` | the catalog contains embedded files |
| `COVER_PAGE_COUNT` | a cover wrap does not contain exactly one PDF page |
| `COVER_SIZE_MISMATCH` | cover width/height differs from trim, bleed, spine, and page-count math |
| `COVER_TEXT_OUTSIDE_SAFE_AREA` | cover text is less than 0.25 inch from an outside edge |
| `SPINE_TEXT_NOT_ALLOWED` | the spine area contains text at 79 effective pages or fewer |
| `SPINE_TEXT_CLEARANCE` | spine text is less than 0.0625 inch from a fold line |

## Warnings

| Code | Trigger |
| --- | --- |
| `PAGE_ROTATED` | page dictionary or layout contains non-zero encoded rotation |
| `TRANSPARENCY_PRESENT` | resource state uses alpha or a soft mask |
| `THIN_LINE` | a detected vector stroke is thinner than 0.75 point |
| `BOOKMARKS_PRESENT` | the document outline contains bookmarks |
| `EXCESSIVE_BLANK_PAGES` | three or more consecutive pages have no text, image, or vector object |

## Informational notes

| Code | Trigger |
| --- | --- |
| `ODD_PAGE_COUNT` | page count will be rounded to an even number for cover math |
| `FONT_SUBSET` | a used font is embedded with a six-letter subset prefix |
| `IMAGE_EXCESSIVE_DPI` | an effective image dimension exceeds the recommended 600 DPI |

An informational note does not change the default exit code. Use `--fail-on warning` to
make warnings block CI.

## Measurement limits

Effective DPI uses image source pixels divided by the placed PDF bounding box. Complex
clipping, repeated patterns, or image transforms can still require visual review.

The safe-area test evaluates extractable PDF text. It cannot see letters rasterized into
an image or converted to vector outlines. ProofMill reports that boundary rather than
pretending OCR or semantic layout inference occurred.

