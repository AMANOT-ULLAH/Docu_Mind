from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import config
from app.api.deps import get_db
from app.db import crud
from app.db.database import Base
from app.main import app
from app.services import worker
from app.validation.duplicates import invoice_key
from app.validation.invoice_validator import validate_invoice

PDF = b"%PDF-1.4\n%fake"


def f(v, ev="x", c="high"):
    return {"value": v, "evidence": ev, "confidence": c}


def invoice(**over):
    base = {"invoice_number": f("INV-1025"), "invoice_date": f("2026-10-15"),
            "supplier_name": f("ABC Ltd"), "customer_name": f("XYZ"),
            "subtotal": f(10000), "tax": f(1500), "total": f(11500),
            "currency": f("BDT"), "line_items": [], "notes": []}
    base.update(over)
    return base


@pytest.fixture
def env(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine, expire_on_commit=False)

    def override():
        with Session(engine, expire_on_commit=False) as s:
            yield s

    app.dependency_overrides[get_db] = override
    submitted = []
    monkeypatch.setattr(worker, "submit", submitted.append)
    monkeypatch.setattr(config, "UPLOAD_DIR", str(tmp_path / "up"))
    yield SimpleNamespace(client=TestClient(app), db=db, submitted=submitted,
                          up=tmp_path / "up", tmp=tmp_path)
    app.dependency_overrides.clear()
    db.close()


def upload(env, *files):
    return env.client.post("/documents", files=[("files", x) for x in files])


def seed(db, ex=None, name="a.pdf", text="hello"):
    ex = ex or invoice()
    rep = validate_invoice(ex)
    d = crud.create_document(db, name, "/tmp/x", "h-" + name)
    crud.save_result(db, d, {
        "extraction": ex, "validation": rep, "provider": "gemini/x",
        "file_seconds": 0.1, "llm_seconds": 1.0, "file_hash": "h-" + name,
        "invoice_key": invoice_key(ex), "text": text, "evidence_flags": [], "errors": [],
        "review_reasons": [f"{i['type']}: {i['field']}" for i in rep["issues"]]})
    return d.id


def test_health(env):
    assert env.client.get("/health").json() == {"status": "ok"}


def test_upload_queues_and_submits(env):
    r = upload(env, ("a.pdf", PDF, "application/pdf"))
    assert r.status_code == 202
    doc = r.json()["documents"][0]
    assert doc["status"] == "queued"
    assert env.submitted == [doc["id"]]
    assert len(list(env.up.iterdir())) == 1


def test_upload_strips_path_from_filename(env):
    r = upload(env, ("../../evil.pdf", PDF, "application/pdf"))
    assert r.json()["documents"][0]["file_name"] == "evil.pdf"
    stored = list(env.up.iterdir())
    assert len(stored) == 1 and stored[0].parent == env.up


def test_upload_rejects_unsupported_type(env):
    r = upload(env, ("run.exe", b"MZ....", "application/octet-stream"))
    assert r.status_code == 400
    assert env.submitted == []


def test_upload_rejects_content_mismatch(env):
    r = upload(env, ("a.pdf", b"just plain text", "application/pdf"))
    assert r.status_code == 400
    assert list(env.up.iterdir()) == []


def test_upload_rejects_too_large(env, monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_MB", 0.001)      # ~1 KB
    r = upload(env, ("a.pdf", PDF + b"x" * 5000, "application/pdf"))
    assert r.status_code == 400
    assert list(env.up.iterdir()) == []


def test_upload_mixed_batch(env):
    r = upload(env, ("a.pdf", PDF, "application/pdf"), ("x.exe", b"MZ", "application/x-msdownload"))
    assert r.status_code == 202
    assert [d["status"] for d in r.json()["documents"]] == ["queued", "rejected"]
    assert len(env.submitted) == 1


def test_detail_shows_progress_and_events(env):
    doc_id = upload(env, ("a.pdf", PDF, "application/pdf")).json()["documents"][0]["id"]
    r = env.client.get(f"/documents/{doc_id}").json()
    assert r["status"] == "queued" and r["progress"] == 0
    assert [e["event"] for e in r["events"]] == ["uploaded"]


def test_missing_document_is_404(env):
    assert env.client.get("/documents/9999").status_code == 404


def test_result_not_ready_is_409(env):
    doc_id = upload(env, ("a.pdf", PDF, "application/pdf")).json()["documents"][0]["id"]
    assert env.client.get(f"/documents/{doc_id}/result").status_code == 409


def test_result_contains_issues(env):
    doc_id = seed(env.db, invoice(total=f(15000)))
    r = env.client.get(f"/documents/{doc_id}/result").json()
    assert r["status"] == "done" and r["needs_review"] is True
    assert "total_mismatch" in [i["type"] for i in r["issues"]]


def test_list_filters(env):
    a = seed(env.db, name="a.pdf")
    b = seed(env.db, invoice(total=f(15000)), name="b.pdf")
    c = crud.create_document(env.db, "c.pdf", "/c", "hc").id
    crud.mark_failed(env.db, crud.get_document(env.db, c), "bad")
    ids = lambda qs: [i["id"] for i in env.client.get("/documents" + qs).json()["items"]]
    assert ids("") == [c, b, a]
    assert ids("?needs_review=true") == [b]
    assert ids("?status=failed") == [c]


def test_keyword_search(env):
    a = seed(env.db, name="alpha.pdf", text="first invoice")
    b = seed(env.db, name="b.pdf", text="contains Rahman Traders here")
    ids = lambda qs: [i["id"] for i in env.client.get("/documents" + qs).json()["items"]]
    assert ids("?q=rahman") == [b]
    assert ids("?q=alpha") == [a]


def test_correction_fixes_total(env):
    doc_id = seed(env.db, invoice(total=f(15000)))
    r = env.client.patch(f"/documents/{doc_id}/result", json={"fields": {"total": 11500}})
    assert r.status_code == 200
    body = r.json()
    assert body["needs_review"] is False and body["issues"] == []
    assert body["extraction"]["total"]["value"] == 15000      # AI-র মূল উত্তর অক্ষত
    assert body["corrected"]["total"]["value"] == 11500


def test_correction_can_create_new_issue(env):
    doc_id = seed(env.db)
    r = env.client.patch(f"/documents/{doc_id}/result", json={"fields": {"total": 99999}}).json()
    assert r["needs_review"] is True
    assert "total_mismatch" in [i["type"] for i in r["issues"]]


def test_correction_bad_input(env):
    doc_id = seed(env.db)
    url = f"/documents/{doc_id}/result"
    assert env.client.patch(url, json={"fields": {"nope": 1}}).status_code == 400
    assert env.client.patch(url, json={"fields": {"total": "abc"}}).status_code == 400
    assert env.client.patch(url, json={}).status_code == 400


def test_correction_rechecks_duplicates(env):
    seed(env.db, name="a.pdf")                                  # INV-1025
    b = seed(env.db, invoice(invoice_number=f("INV-1")), name="b.pdf")
    r = env.client.patch(f"/documents/{b}/result",
                         json={"fields": {"invoice_number": "INV-1025"}}).json()
    assert "duplicate_invoice" in [i["type"] for i in r["issues"]]


def test_approve_clears_review_flag(env):
    doc_id = seed(env.db, invoice(total=f(15000)))
    assert env.client.post(f"/documents/{doc_id}/approve").json()["needs_review"] is False
    events = [e["event"] for e in env.client.get(f"/documents/{doc_id}").json()["events"]]
    assert "approved" in events


def test_approve_requires_done(env):
    doc_id = upload(env, ("a.pdf", PDF, "application/pdf")).json()["documents"][0]["id"]
    assert env.client.post(f"/documents/{doc_id}/approve").status_code == 409


def test_reprocess_failed(env):
    p = env.tmp / "f.pdf"
    p.write_bytes(PDF)
    d = crud.create_document(env.db, "f.pdf", str(p), "h")
    crud.mark_failed(env.db, d, "boom")
    r = env.client.post(f"/documents/{d.id}/reprocess")
    assert r.status_code == 202 and r.json()["status"] == "queued"
    assert env.submitted == [d.id]


def test_reprocess_done_is_409(env):
    doc_id = seed(env.db)
    assert env.client.post(f"/documents/{doc_id}/reprocess").status_code == 409


def test_reprocess_missing_file_is_410(env):
    d = crud.create_document(env.db, "f.pdf", str(env.tmp / "gone.pdf"), "h")
    crud.mark_failed(env.db, d, "boom")
    assert env.client.post(f"/documents/{d.id}/reprocess").status_code == 410


def test_detail_shows_page_progress_and_stage(env):
    doc_id = upload(env, ("a.pdf", PDF, "application/pdf")).json()["documents"][0]["id"]
    d = crud.get_document(env.db, doc_id)
    crud.set_status(env.db, d, "processing")
    crud.set_progress(env.db, d, 40, 100)
    r = env.client.get(f"/documents/{doc_id}").json()
    assert (r["pages_done"], r["pages_total"], r["stage"]) == (40, 100, "reading")
    listed = env.client.get("/documents").json()["items"][0]
    assert (listed["pages_done"], listed["pages_total"]) == (40, 100)
    crud.set_progress(env.db, d, 100, 100)
    assert env.client.get(f"/documents/{doc_id}").json()["stage"] == "extracting"


def test_stage_is_plain_status_without_page_info(env):
    doc_id = upload(env, ("a.pdf", PDF, "application/pdf")).json()["documents"][0]["id"]
    assert env.client.get(f"/documents/{doc_id}").json()["stage"] == "queued"
