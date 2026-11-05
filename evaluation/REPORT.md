# DocuMind Evaluation Report

## 1. Setup

- Dataset: `evaluation/dataset/` (34 files, labels in `labels.json`)
  - 32 valid documents (digital PDF, scanned PDF, image, CSV, USD, no-tax, planted-error and duplicate cases)
  - 2 deliberately bad files (should fail or be flagged)
- Runner: `evaluation/run_eval.py` (runs the real `process_and_extract` pipeline, no mocks)
- Fields scored (8): `invoice_number`, `invoice_date`, `supplier_name`, `customer_name`, `subtotal`, `tax`, `total`, `currency`
- Matching rules: text fields compared after normalisation (lowercase, alphanumerics only); money fields within ±0.01; line items matched on description, quantity, unit price and amount
- Models compared: Gemini 3.1 and Gemini 3.5 (same dataset, same code)
- Raw results: `results/results_3.1.json`, `results/results_3.5.json`

## 2. Headline results

| Metric | Gemini 3.1 | Gemini 3.5 |
|---|---|---|
| Files processed | 34 | 34 |
| Valid documents | 32 | 32 |
| Extraction success rate | 100.0% | 100.0% |
| Failure rate | 0.0% | 0.0% |
| Crashes | 0 | 0 |
| Bad files handled correctly | 2/2 | 2/2 |
| All outcomes as expected | 100.0% | 100.0% |
| Field accuracy | 89.8% | 90.2% |
| Fully correct documents | 26/32 | 27/32 |
| Line item accuracy | 89.0% (81/91) | 89.0% (81/91) |
| Invented line items | 0 | 0 |
| Invented field values | none | none |

## 3. Per-field accuracy

| Field | Gemini 3.1 | Gemini 3.5 |
|---|---|---|
| invoice_number | 90.6% | 90.6% |
| invoice_date | 87.5% | 90.6% |
| supplier_name | 90.6% | 90.6% |
| customer_name | 90.6% | 90.6% |
| subtotal | 90.6% | 90.6% |
| tax | 87.5% | 87.5% |
| total | 90.6% | 90.6% |
| currency | 90.6% | 90.6% |

Note: if extraction fails for a file, all of its fields are counted as wrong.

## 4. Safety: wrong values vs. review flags

| Metric | Gemini 3.1 | Gemini 3.5 |
|---|---|---|
| Documents with at least one wrong value | 6 | 5 |
| Of those, flagged for human review | 6 | 5 |
| Silent errors (wrong and not flagged) | 0 | 0 |
| False alarms on correct documents | 0/22 (0.0%) | 0/23 (0.0%) |

In both runs every document with a wrong value was flagged for review, and no correct document was flagged. The system does not pass errors through silently.

## 5. Validation and duplicate detection

Planted problems and what the validator reported (identical in both runs):

| File | Planted problem | Detected as |
|---|---|---|
| `dup_copy_of_digital_01.pdf` | byte-identical copy | `duplicate_file` |
| `dup_image_of_digital_01.png` | same invoice, different file | `duplicate_invoice` |
| `wrong_total_01.pdf` | total does not match subtotal + tax | `total_mismatch` |
| `line_mismatch_01.pdf` | line items do not add up | `line_item_mismatch` |

## 6. Processing time (seconds per file)

| | Gemini 3.1 | Gemini 3.5 |
|---|---|---|
| Mean | 7.91 | 11.4 |
| Median | 5.79 | 7.63 |
| p95 | 18.4 | 28.59 |
| Max | 55.0 | 92.5 |
| Total (34 files) | 268.9 | 387.5 |
| Mean LLM time | 6.69 | 10.3 |
| Mean file-processing time (PDF, OCR) | 1.41 | 1.4 |

Almost all of the time is the LLM call. Local file processing takes about 1.4 s per file.

### 6.1 Large-file processing

These runs measure file reading and OCR only (the `processing` line below), not the LLM call.

| File | Size | Pages | Processing time | Time per page | Peak memory | Extracted text |
|---|---|---|---|---|---|---|
| `digital_1000.pdf` (digital) | 6.7 MB | 1000 | 2.9 s | 0.003 s | 184 MB | 1,187,000 chars (~297k tokens, rough estimate) |
| `scanned_60.pdf` (scanned, OCR) | 9.1 MB | 60 | 246.1 s | 4.1 s | 494 MB | 67,080 chars (~17k tokens, rough estimate) |

Both runs finished with status success, all pages read, and no errors or warnings.

- Digital PDFs are fast: a 1000-page file is read in under 3 seconds with modest memory.
- OCR dominates the cost for scanned files, at about 4 seconds per page in this run, so scanned documents take minutes, not seconds. This is why processing runs in the background with page-level progress.
- A 1000-page document produces roughly 297k tokens of text. Sending that in one LLM call is not implemented as chunked extraction (see section 9), and this run did not test the LLM step on it.

Other large-file runs are in `results/big_scanned_10.txt` and `results/big_scanned.txt`.

## 7. Model comparison

- Accuracy is nearly the same. Gemini 3.5 is slightly higher (+0.4 points field accuracy, one more fully correct document, better on `invoice_date`).
- Gemini 3.5 is about 44% slower on average and has a worse worst-case time.
- Line item accuracy is identical.
- Safety behaviour is identical: 0 silent errors, 0 false alarms.

## 8. Failure analysis

Five of the 32 valid documents had at least one wrong value in the Gemini 3.5 run. All five were flagged for review.

| File | Kind | What went wrong | Flagged |
|---|---|---|---|
| `scanned_01.pdf` | scanned PDF | All 8 fields correct; 2 of 3 line items matched | Yes |
| `image_noisy_1_01.jpg` | noisy image (level 1) | `tax` wrong; all other fields and 4/4 line items correct | Yes |
| `image_noisy_3_01.jpg` | noisy image (level 3) | All 8 fields wrong, 0 of 2 line items | Yes |
| `image_noisy_3_02.jpg` | noisy image (level 3) | All 8 fields wrong, 0 of 3 line items | Yes |
| `image_noisy_3_03.jpg` | noisy image (level 3) | All 8 fields wrong, 0 of 4 line items | Yes |

Findings:

- The three complete failures are all in the `image_noisy_3` group, the noisiest images in the dataset. The system returned no usable values for them (no line items extracted) and flagged each one for human review instead of guessing.
- The "100% extraction success rate" counts a document as extracted if the pipeline produced a result. These three produced results with no usable content, so the stricter measure is field accuracy (about 90%), not the success rate.
- Excluding the three `image_noisy_3` files, all other documents have no wrong field except one `tax` value (`image_noisy_1_01.jpg`) and one missed line item (`scanned_01.pdf`).
- The planted-error files (`wrong_total_01.pdf`, `line_mismatch_01.pdf`, duplicates) are not among the failures above: their values were extracted as labelled, and the validator flagged the planted problem (see section 5).

Improvement ideas (not implemented): image pre-processing (denoise, deskew, contrast) before OCR, and re-running low-confidence images with a second model.

## 9. Limitations

- The dataset is small (34 files) and partly synthetic, so these numbers are indicative, not a guarantee for real-world invoices.
- Free-tier quotas apply, so runs are throttled (`--sleep 4`).
- Cross-document verification (PDF vs. PDF, PDF vs. Excel) is not evaluated here.
