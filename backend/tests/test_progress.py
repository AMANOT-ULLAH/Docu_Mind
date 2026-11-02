import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import crud
from app.db.database import Base
from app.services import progress as prog
from app.services import ingest


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    from contextlib import contextmanager

    @contextmanager
    def session():
        with Session(engine, expire_on_commit=False) as s:
            yield s
            s.commit()

    monkeypatch.setattr(prog, "get_session", session)
    with Session(engine, expire_on_commit=False) as s:
        yield s


def read(s, doc_id):
    s.expire_all()
    d = crud.get_document(s, doc_id)
    return d.pages_done, d.pages_total


def test_writes_progress(db):
    d = crud.create_document(db, "a.pdf", "/x", "h")
    w = prog.ProgressWriter(d.id, min_interval=0)
    w(3, 10)
    assert read(db, d.id) == (3, 10)


def test_throttles_but_always_writes_last_page(db):
    d = crud.create_document(db, "a.pdf", "/x", "h")
    w = prog.ProgressWriter(d.id, min_interval=60)
    w(1, 5)               # প্রথমটা লেখা হয়
    w(2, 5)               # সময়ের মধ্যে, বাদ
    w(3, 5)               # বাদ
    assert read(db, d.id) == (1, 5)
    w(5, 5)               # শেষ পেজ সবসময় লেখা হয়
    assert read(db, d.id) == (5, 5)


def test_failure_in_write_is_swallowed(monkeypatch):
    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(prog, "get_session", boom)
    prog.ProgressWriter(1, min_interval=0)(1, 2)     # exception ছোঁড়ে না


def test_set_status_resets_progress(db):
    d = crud.create_document(db, "a.pdf", "/x", "h")
    d.pages_done, d.pages_total = 7, 10
    db.commit()
    crud.set_status(db, d, "queued", "reprocess")
    assert d.pages_done == 0


def test_ingest_passes_a_progress_writer(db, tmp_path, monkeypatch):
    f = tmp_path / "a.pdf"
    f.write_bytes(b"%PDF-1.4")
    seen = {}

    def fake(path, known=None, progress=None):
        seen["progress"] = progress
        return {"extraction": None, "errors": ["x"], "review_reasons": [], "file_hash": "h"}

    monkeypatch.setattr(ingest, "process_and_extract", fake)
    ingest.ingest_file(db, f)
    assert isinstance(seen["progress"], prog.ProgressWriter)
