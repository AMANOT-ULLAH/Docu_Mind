# AI prompts used during development

Tool: Claude (Anthropic), chat interface. The author wrote prompts in Bengali (partly romanised); they are paraphrased in English here. The product itself calls Gemini; its extraction prompt is in `backend/app/extraction/prompts.py`.

## Final-stage prompts (delivery, documentation, evaluation)

| # | Purpose | Prompt (paraphrased) |
|---|---|---|
| 1 | Gap analysis | "Here is the project task and my current state. Check what is still left to do." |
| 2 | Fix startup problems | "I came back to the project after a long time and it will not run. Here is the terminal output." (uvicorn import error, Docker `POSTGRES_PASSWORD` error) |
| 3 | Finish and commit | "Replace splitter.py with this version, run the tests, then commit." |
| 4 | Evaluation analysis | "Here is the output of `run_eval.py` and the saved results. Build the evaluation report from the real numbers." |
| 5 | Failure analysis | "Which documents are wrong in the results, and why?" |
| 6 | Documentation | "Here are models.py, config.py and the API routes. Write the README with architecture, DB schema and setup steps." |
| 7 | Final review | "Check everything step by step against the screenshots and the README. Is anything left?" |

## Earlier prompts

The earlier development was spread over several chats. It is summarised here by area (what the AI was asked to help with), not as word-for-word prompts.

| Area | What the AI was asked to help with |
|---|---|
| File processing | Read digital PDFs, scanned PDFs, images, Excel and CSV; route each file to the right processor; run OCR on pages in parallel |
| Extraction | Design the extraction schema (value, confidence, evidence per field), write the Gemini prompt, add a fallback provider and model retry |
| Validation | Check that subtotal + tax = total, line items add up, required fields exist; detect duplicate files (hash) and duplicate invoices (key) |
| API and background work | FastAPI endpoints for upload, list, detail, correction, approve and reprocess; background worker; page-level progress |
| Database and search | PostgreSQL models, processing history, pgvector embeddings, keyword, semantic and hybrid search |
| Frontend | React pages for upload, document list with progress bars, detail and correction, and search |
| Testing and evaluation | Write the 119 automated tests, build the labelled dataset, write `run_eval.py`, compare Gemini model versions |
| Large files | Benchmark a 1000-page digital PDF and scanned PDFs up to 200 pages |
| Invoice splitter | Utility that splits a multi-invoice PDF by invoice number (tested, not wired into the pipeline) |

## How AI output was checked

- Code was run locally; 119 automated tests pass.
- Evaluation numbers come from real runs on the labelled dataset (`evaluation/results/`).
- AI suggestions that did not fit the code base (for example wrong run commands) were corrected after running them.
