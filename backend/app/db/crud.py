from sqlalchemy import or_, select
from sqlalchemy.orm import defer, selectinload

from app.db.models import Document, Extraction, ProcessingEvent, ValidationIssue


def add_event(s, doc, event, message=None):
    doc.events.append(ProcessingEvent(event=event, message=message))
    s.commit()


def create_document(s, file_name, stored_path, fhash):
    doc = Document(file_name=file_name, stored_path=stored_path,
                   file_hash=fhash, status="queued")
    doc.events.append(ProcessingEvent(event="uploaded", message=file_name))
    s.add(doc)
    s.commit()
    return doc


def set_status(s, doc, status, message=None):
    doc.status = status
    doc.events.append(ProcessingEvent(event=status, message=message))
    s.commit()


def mark_failed(s, doc, error):
    doc.status = "failed"
    doc.error = str(error)[:1000]
    doc.events.append(ProcessingEvent(event="failed", message=doc.error))
    s.commit()


def known_records(s, exclude_id=None):
    """duplicate যাচাইয়ের জন্য আগে সফলভাবে প্রসেস হওয়া document-এর hash ও key।"""
    q = select(Document.id, Document.file_hash, Document.invoice_key).where(
        Document.status == "done")
    if exclude_id is not None:
        q = q.where(Document.id != exclude_id)
    return [{"id": r.id, "file_hash": r.file_hash, "key": r.invoice_key}
            for r in s.execute(q).all()]


def save_result(s, doc, out):
    """process_and_extract-এর ফলাফল (dict) DB-তে রাখে। আবার চালালে আগের ফল বদলে যায়।"""
    # reprocess হলে আগের ফল সরাও
    doc.extraction = None
    doc.issues.clear()
    s.flush()

    doc.extracted_text = out.get("text")
    doc.file_hash = out.get("file_hash") or doc.file_hash

    if out.get("extraction") is None:
        reasons = list(out.get("errors") or []) + list(out.get("review_reasons") or [])
        mark_failed(s, doc, "; ".join(reasons) or "extraction failed")
        return doc

    doc.invoice_key = out.get("invoice_key")
    doc.review_reasons = out.get("review_reasons") or []
    doc.needs_review = bool(doc.review_reasons)
    doc.error = None

    doc.extraction = Extraction(
        result=out["extraction"], provider=out.get("provider"),
        file_seconds=out.get("file_seconds"), llm_seconds=out.get("llm_seconds"))

    for i in (out.get("validation") or {}).get("issues", []):
        doc.issues.append(ValidationIssue(
            type=i["type"], field=i["field"], severity=i["severity"],
            message=i["message"], expected=i["expected"], actual=i["actual"]))
    for flag in out.get("evidence_flags") or []:
        field, _, msg = flag.partition(": ")
        doc.issues.append(ValidationIssue(
            type="evidence_not_found", field=field, severity="warning",
            message=msg or flag))

    doc.status = "done"
    doc.events.append(ProcessingEvent(
        event="extracted",
        message=f"{out.get('provider')} | file {out.get('file_seconds')}s, "
                f"LLM {out.get('llm_seconds')}s"))
    s.commit()
    return doc


def get_document(s, doc_id):
    return s.get(Document, doc_id)


def list_documents(s, status=None, needs_review=None, q=None, limit=50, offset=0):
    stmt = (select(Document)
            .options(selectinload(Document.extraction), defer(Document.extracted_text))
            .order_by(Document.id.desc()))
    if status:
        stmt = stmt.where(Document.status == status)
    if needs_review is not None:
        stmt = stmt.where(Document.needs_review == needs_review)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Document.file_name.ilike(like),
                              Document.invoice_key.ilike(like),
                              Document.extracted_text.ilike(like)))
    return list(s.execute(stmt.limit(limit).offset(offset)).scalars())