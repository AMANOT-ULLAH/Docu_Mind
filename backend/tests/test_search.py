import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import crud
from app.db.database import Base
from app.search import embeddings, service


@pytest.fixture
def s():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session


def fake_embed(texts, task="RETRIEVAL_DOCUMENT", batch=50):
    """নকল embedding: 'apple' শব্দ থাকলে এক দিকে, 'steel' থাকলে আরেক দিকে।"""
    out = []
    for t in texts:
        t = t.lower()
        v = [1.0 if "apple" in t else 0.0, 1.0 if "steel" in t else 0.0, 0.1]
        out.append(embeddings.normalize(v))
    return out


@pytest.fixture(autouse=True)
def patch_embed(monkeypatch):
    monkeypatch.setattr(embeddings, "embed_texts", fake_embed)
    monkeypatch.setattr(embeddings, "embed_query", lambda q: fake_embed([q])[0])


def add_doc(s, name, text):
    d = crud.create_document(s, name, "/x", "h-" + name)
    d.extracted_text = text
    d.status = "done"
    s.commit()
    return d


def test_chunking_splits_long_text_with_overlap():
    chunks = embeddings.chunk_text("a" * 3000, size=1500, overlap=200)
    assert len(chunks) == 3
    assert chunks[0][-200:] == chunks[1][:200]


def test_chunking_empty():
    assert embeddings.chunk_text("") == []
    assert embeddings.chunk_text(None) == []


def test_normalize_unit_length():
    v = embeddings.normalize([3.0, 4.0])
    assert abs(sum(x * x for x in v) - 1.0) < 1e-9


def test_index_creates_chunks_and_reindex_replaces(s):
    d = add_doc(s, "a.pdf", "apple " * 600)
    n1 = service.index_document(s, d)
    n2 = service.index_document(s, d)
    assert n1 == n2 > 1
    from app.db.models import DocumentChunk
    assert s.query(DocumentChunk).count() == n2


def test_semantic_search_ranks_by_meaning(s):
    a = add_doc(s, "a.pdf", "invoice for apple juice")
    b = add_doc(s, "b.pdf", "invoice for steel pipes")
    service.index_document(s, a)
    service.index_document(s, b)
    hits = service.semantic_search(s, "apple")
    assert hits[0][0] == a.id
    hits = service.semantic_search(s, "steel")
    assert hits[0][0] == b.id


def test_semantic_returns_one_hit_per_document(s):
    a = add_doc(s, "a.pdf", "apple " * 1000)
    service.index_document(s, a)
    hits = service.semantic_search(s, "apple")
    assert [h[0] for h in hits] == [a.id]


def test_keyword_search(s):
    a = add_doc(s, "alpha.pdf", "hello Rahman Traders")
    add_doc(s, "b.pdf", "nothing")
    assert service.keyword_ids(s, "rahman") == [a.id]


def test_hybrid_combines_both(s):
    a = add_doc(s, "a.pdf", "apple juice")
    b = add_doc(s, "b.pdf", "steel pipes with Rahman")
    service.index_document(s, a)
    service.index_document(s, b)
    ids = [h[0] for h in service.hybrid_search(s, "apple")]
    assert a.id in ids