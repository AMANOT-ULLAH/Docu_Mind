import time
from pathlib import Path

from .common import MAX_FILE_SIZE, detect_type, sha256_of
from .schemas import ExtractionResult
from .pdf_processor import extract_pdf_pages
from .image_processor import extract_image_pages
from .excel_processor import extract_excel
from .csv_processor import extract_csv


def process_document(path) -> ExtractionResult:
    """যেকোনো ফাইল নেয়, কখনো crash করে না, সবসময় ExtractionResult ফেরত দেয়।"""
    path = Path(path)
    start = time.perf_counter()
    result = ExtractionResult(
        file_name=path.name, file_type="unknown", file_hash="", status="failed"
    )
    try:
        if not path.exists():
            raise FileNotFoundError("File not found")
        size = path.stat().st_size
        if size == 0:
            raise ValueError("File is empty")
        if size > MAX_FILE_SIZE:
            raise ValueError(f"File exceeds {MAX_FILE_SIZE // (1024 * 1024)} MB limit")

        result.file_type = detect_type(path)      # unsupported হলে ValueError
        result.file_hash = sha256_of(path)

        if result.file_type == "pdf":
            pages, warnings = extract_pdf_pages(path)
            tables = []
        elif result.file_type == "image":
            pages, warnings = extract_image_pages(path)
            tables = []
        elif result.file_type == "excel":
            pages, tables, warnings = extract_excel(path)
        else:
            pages, tables, warnings = extract_csv(path)

        result.pages, result.tables, result.warnings = pages, tables, warnings

        if not pages:
            result.status = "failed"
            result.errors.append("No content could be extracted")
        elif any("failed" in w for w in warnings):
            result.status = "partial"       # কিছু page/sheet fail, বাকিগুলো সফল
        else:
            result.status = "success"

    except Exception as e:
        result.status = "failed"
        result.errors.append(f"{type(e).__name__}: {e}")

    result.processing_seconds = round(time.perf_counter() - start, 3)
    return result