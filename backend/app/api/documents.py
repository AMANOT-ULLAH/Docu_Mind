import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import config
from app.api.deps import get_db
from app.db import crud
from app.services import corrections, worker
from app.validation.duplicates import file_hash

router = APIRouter()

ALLOWED = {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".xlsx", ".xls", ".csv"}
MAX_FILES_PER_REQUEST = 20
PROGRESS = {"queued": 0, "processing": 50, "done": 100, "failed": 100}


class _Reject(Exception):
    pass


def _signature_ok(ext, head):
    """ফাইলের শুরুর বাইট নামের extension-এর সাথে মেলে কি না (নাম বদলে ভুয়া ফাইল ঠেকাতে)।"""
    if ext == ".pdf":
        return b"%PDF" in head[:1024]
    if ext == ".png":
        return head.startswith(b"\x89PNG")
    if ext in (".jpg", ".jpeg"):
        return head.startswith(b"\xff\xd8")
    if ext in (".tif", ".tiff"):
        return head[:4] in (b"II*\x00", b"MM\x00*")
    if ext == ".xlsx":
        return head.startswith(b"PK")
    if ext == ".xls":
        return head.startswith(b"\xd0\xcf\x11\xe0")
    if ext == ".csv":
        return b"\x00" not in head
    return False


def _store(f: UploadFile):
    name = os.path.basename((f.filename or "").replace("\\", "/")) or "unnamed"
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED:
        raise _Reject(f"unsupported file type '{ext or 'none'}'")
    limit = int(config.MAX_UPLOAD_MB * 1024 * 1024)
    folder = Path(config.UPLOAD_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"{uuid.uuid4().hex}{ext}"        # ইউজারের দেওয়া নাম কখনো path-এ যায় না
    size = 0
    try:
        with open(dest, "wb") as out:
            while chunk := f.file.read(1024 * 1024):
                if size == 0 and not _signature_ok(ext, chunk[:1024]):
                    raise _Reject("file content does not match its extension")
                size += len(chunk)
                if size > limit:
                    raise _Reject(f"file is larger than {config.MAX_UPLOAD_MB:g} MB")
                out.write(chunk)
        if size == 0:
            raise _Reject("file is empty")
    except _Reject:
        dest.unlink(missing_ok=True)
        raise
    return name, dest


def _doc(db, doc_id):
    d = crud.get_document(db, doc_id)
    if d is None:
        raise HTTPException(404, "document not found")
    return d


def _effective(d):
    e = d.extraction
    return None if e is None else (e.corrected or e.result)


def _summary(d):
    ex = _effective(d) or {}

    def v(k):
        return (ex.get(k) or {}).get("value")

    return {"id": d.id, "file_name": d.file_name, "status": d.status,
            "needs_review": d.needs_review, "created_at": d.created_at.isoformat(),
            "invoice_number": v("invoice_number"), "supplier_name": v("supplier_name"),
            "total": v("total"), "currency": v("currency"), "error": d.error}


def _result_payload(d):
    e = d.extraction
    return {
        "document_id": d.id, "status": d.status, "needs_review": d.needs_review,
        "review_reasons": d.review_reasons or [],
        "extraction": e.result, "corrected": e.corrected, "effective": e.corrected or e.result,
        "provider": e.provider, "file_seconds": e.file_seconds, "llm_seconds": e.llm_seconds,
        "issues": [{"id": i.id, "type": i.type, "field": i.field, "severity": i.severity,
                    "message": i.message, "expected": i.expected, "actual": i.actual,
                    "resolved": i.resolved} for i in d.issues],
    }


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/documents", status_code=202)
def upload(files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    if len(files) > MAX_FILES_PER_REQUEST:
        raise HTTPException(400, f"at most {MAX_FILES_PER_REQUEST} files per request")
    results = []
    for f in files:
        try:
            name, dest = _store(f)
        except _Reject as e:
            results.append({"file_name": os.path.basename(f.filename or ""),
                            "status": "rejected", "error": str(e)})
            continue
        doc = crud.create_document(db, name[:255], str(dest), file_hash(dest))
        worker.submit(doc.id)                     # প্রসেস পেছনে চলবে, এখানে অপেক্ষা নেই
        results.append({"id": doc.id, "file_name": doc.file_name, "status": "queued"})
    if not any("id" in r for r in results):
        raise HTTPException(400, detail=results)
    return {"documents": results}


@router.get("/documents")
def list_docs(status: Optional[str] = None, needs_review: Optional[bool] = None,
              q: Optional[str] = Query(None, max_length=200),
              limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
              db: Session = Depends(get_db)):
    docs = crud.list_documents(db, status=status, needs_review=needs_review,
                               q=q, limit=limit, offset=offset)
    return {"items": [_summary(d) for d in docs], "limit": limit, "offset": offset}


@router.get("/documents/{doc_id}")
def detail(doc_id: int, db: Session = Depends(get_db)):
    d = _doc(db, doc_id)
    return {**_summary(d), "progress": PROGRESS.get(d.status, 0),
            "review_reasons": d.review_reasons or [],
            "events": [{"event": e.event, "message": e.message, "at": e.created_at.isoformat()}
                       for e in d.events]}


@router.get("/documents/{doc_id}/result")
def result(doc_id: int, db: Session = Depends(get_db)):
    d = _doc(db, doc_id)
    if d.status != "done" or d.extraction is None:
        raise HTTPException(409, {"status": d.status, "error": d.error,
                                  "message": "result is not available"})
    return _result_payload(d)


class LineItemIn(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None


class Correction(BaseModel):
    fields: dict[str, str | int | float | None] = {}
    line_items: Optional[list[LineItemIn]] = None


@router.patch("/documents/{doc_id}/result")
def correct(doc_id: int, body: Correction, db: Session = Depends(get_db)):
    d = _doc(db, doc_id)
    items = None if body.line_items is None else [li.model_dump() for li in body.line_items]
    try:
        corrections.apply_correction(db, d, body.fields, items)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _result_payload(d)


@router.post("/documents/{doc_id}/approve")
def approve(doc_id: int, db: Session = Depends(get_db)):
    d = _doc(db, doc_id)
    if d.status != "done":
        raise HTTPException(409, "only processed documents can be approved")
    d.needs_review = False
    crud.add_event(db, d, "approved", "marked as reviewed")
    return _summary(d)


@router.post("/documents/{doc_id}/reprocess", status_code=202)
def reprocess(doc_id: int, db: Session = Depends(get_db)):
    d = _doc(db, doc_id)
    if d.status != "failed":
        raise HTTPException(409, "only failed documents can be reprocessed")
    if not d.stored_path or not Path(d.stored_path).exists():
        raise HTTPException(410, "original file is no longer available")
    crud.set_status(db, d, "queued", "reprocess requested")
    worker.submit(d.id)
    return {"id": d.id, "status": d.status}