import logging
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select

from app import config
from app.db import crud
from app.db.database import get_session
from app.db.models import Document
from app.services import ingest

log = logging.getLogger("documind.worker")
_pool = ThreadPoolExecutor(max_workers=config.MAX_WORKERS, thread_name_prefix="doc-worker")


def _run(doc_id):
    try:
        with get_session() as s:
            doc = crud.get_document(s, doc_id)
            if doc is not None:
                ingest.process_existing(s, doc)
    except Exception:
        log.exception("worker crashed on document %s", doc_id)


def submit(doc_id):
    _pool.submit(_run, doc_id)


def requeue_unfinished():
    """সার্ভার বন্ধ হওয়ার সময় যেগুলো আটকে ছিল (queued/processing), চালু হলে আবার কাজে লাগায়।"""
    with get_session() as s:
        ids = [d.id for d in s.scalars(
            select(Document).where(Document.status.in_(["queued", "processing"])))]
    for i in ids:
        submit(i)
    return len(ids)