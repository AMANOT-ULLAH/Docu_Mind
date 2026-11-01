from pathlib import Path

from app.db import crud
from app.services.pipeline import process_and_extract
from app.validation.duplicates import file_hash


def process_existing(s, doc):
    """আগে থেকে DB-তে থাকা document প্রসেস করে। crash করলে 'failed' হয়, বাইরে exception যায় না।"""
    crud.set_status(s, doc, "processing")
    try:
        known = crud.known_records(s, exclude_id=doc.id)
        out = process_and_extract(doc.stored_path, known=known)
        crud.save_result(s, doc, out)
    except Exception as e:
        s.rollback()
        crud.mark_failed(s, doc, f"{type(e).__name__}: {e}")
    return doc


def ingest_file(s, path, name=None):
    path = Path(path)
    doc = crud.create_document(s, name or path.name, str(path), file_hash(path))
    return process_existing(s, doc)