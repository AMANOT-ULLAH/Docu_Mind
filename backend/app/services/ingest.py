from pathlib import Path

from app.db import crud
from app.services.pipeline import process_and_extract
from app.validation.duplicates import file_hash


def ingest_file(s, path, name=None):
    """একটা ফাইল DB-তে নথিভুক্ত করে প্রসেস করে। কিছু crash করলে document 'failed' হয়, বাকিরা চলে।"""
    path = Path(path)
    doc = crud.create_document(s, name or path.name, str(path), file_hash(path))
    crud.set_status(s, doc, "processing")
    try:
        known = crud.known_records(s, exclude_id=doc.id)
        out = process_and_extract(str(path), known=known)
        crud.save_result(s, doc, out)
    except Exception as e:
        s.rollback()
        crud.mark_failed(s, doc, f"{type(e).__name__}: {e}")
    return doc