import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db import crud, models
from app.db.database import Base
from app.services import ingest


@pytest.fixture
def s():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session


def issue(type_="total_mismatch", field="total", severity="error"):
    return {"type": type_, "field": field, "severity": severity,
            "message": "m", "expected": "1", "actual": "2"}


def fake_out(**over):
    out = {
        "file": "a.pdf", "file_seconds": 0.1, "llm_seconds": 1.0, "seconds": 1.1,
        "file_hash": "h1", "invoice_key": "inv1|abc|20261015",
        "doc_status": "success", "extraction": {"total": {"value": 1}},
        "validation": {"status": "ok", "issues": []}, "provider": "gemini/x",
        "evidence_flags": [], "review_reasons": [], "errors": [], "text": "hello",
    }
    out.update(over)
    return out


def test_create_document_is_queued_with_upload_event(s):
    d = crud.create_document(s, "a.pdf", "/tmp/a.pdf", "h1")
    assert d.status == "queued"
    assert [e.event for e in d.events] == ["uploaded"]


def test_save_result_stores_everything(s):
    d = crud.create_document(s, "a.pdf", "/tmp/a.pdf", "h1")
    out = fake_out(
        validation={"status": "review_required", "issues": [issue()]},
        review_reasons=["total_mismatch: total"],
        evidence_flags=["currency: value does not match its evidence line"])
    crud.save_result(s, d, out)
    assert d.status == "done"
    assert d.needs_review is True
    assert d.invoice_key == "inv1|abc|20261015"
    assert d.extracted_text == "hello"
    assert d.extraction.result == {"total": {"value": 1}}
    assert sorted(i.type for i in d.issues) == ["evidence_not_found", "total_mismatch"]
    assert "extracted" in [e.event for e in d.events]


def test_clean_result_does_not_need_review(s):
    d = crud.create_document(s, "a.pdf", "/tmp/a.pdf", "h1")
    crud.save_result(s, d, fake_out())
    assert d.status == "done"
    assert d.needs_review is False
    assert d.issues == []


def test_reprocess_replaces_old_result(s):
    d = crud.create_document(s, "a.pdf", "/tmp/a.pdf", "h1")
    crud.save_result(s, d, fake_out(
        validation={"status": "review_required", "issues": [issue()]},
        review_reasons=["x"]))
    crud.save_result(s, d, fake_out())          # দ্বিতীয়বার, এবার পরিষ্কার
    assert d.issues == []
    assert d.needs_review is False
    assert s.scalar(select(func.count()).select_from(models.Extraction)) == 1


def test_failed_extraction_marks_document_failed(s):
    d = crud.create_document(s, "a.pdf", "/tmp/a.pdf", "h1")
    crud.save_result(s, d, fake_out(extraction=None, errors=["boom"],
                                    review_reasons=["all LLM providers failed"]))
    assert d.status == "failed"
    assert "boom" in d.error
    assert d.extraction is None


def test_known_records_only_done_and_excludes_self(s):
    a = crud.create_document(s, "a.pdf", "/a", "h1")
    crud.save_result(s, a, fake_out())
    b = crud.create_document(s, "b.pdf", "/b", "h2")
    crud.mark_failed(s, b, "bad file")
    c = crud.create_document(s, "c.pdf", "/c", "h3")
    known = crud.known_records(s, exclude_id=c.id)
    assert known == [{"id": a.id, "file_hash": "h1", "key": "inv1|abc|20261015"}]


def test_list_documents_filters(s):
    a = crud.create_document(s, "a.pdf", "/a", "h1")
    crud.save_result(s, a, fake_out(review_reasons=["x"]))
    b = crud.create_document(s, "b.pdf", "/b", "h2")
    crud.save_result(s, b, fake_out())
    c = crud.create_document(s, "c.pdf", "/c", "h3")
    crud.mark_failed(s, c, "bad")
    assert {d.id for d in crud.list_documents(s, status="done")} == {a.id, b.id}
    assert [d.id for d in crud.list_documents(s, needs_review=True)] == [a.id]
    assert [d.id for d in crud.list_documents(s, status="failed")] == [c.id]


def test_deleting_document_deletes_children(s):
    d = crud.create_document(s, "a.pdf", "/a", "h1")
    crud.save_result(s, d, fake_out(
        validation={"status": "review_required", "issues": [issue()]},
        review_reasons=["x"]))
    s.delete(d)
    s.commit()
    for model in (models.Extraction, models.ValidationIssue, models.ProcessingEvent):
        assert s.scalar(select(func.count()).select_from(model)) == 0


def test_ingest_passes_previous_documents_as_known(s, tmp_path, monkeypatch):
    f1, f2 = tmp_path / "a.pdf", tmp_path / "b.pdf"
    f1.write_bytes(b"one")
    f2.write_bytes(b"two")
    seen = []

    def fake_pipeline(path, known=None, progress=None):
        seen.append(known)
        return fake_out()

    monkeypatch.setattr(ingest, "process_and_extract", fake_pipeline)
    d1 = ingest.ingest_file(s, f1)
    ingest.ingest_file(s, f2)
    assert seen[0] == []
    assert seen[1][0]["id"] == d1.id


def test_ingest_crash_marks_failed_instead_of_raising(s, tmp_path, monkeypatch):
    f = tmp_path / "a.pdf"
    f.write_bytes(b"one")

    def boom(path, known=None, progress=None):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(ingest, "process_and_extract", boom)
    d = ingest.ingest_file(s, f)
    assert d.status == "failed"
    assert "kaboom" in d.error