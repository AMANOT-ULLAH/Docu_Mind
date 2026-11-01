import re

from sqlalchemy import select, text as sql

from app.db.models import Document, DocumentChunk
from app.search import embeddings


def index_document(s, doc):
    """document-এর text টুকরো করে embedding বানিয়ে রাখে। আবার চালালে আগেরগুলো বদলে যায়।"""
    s.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
    chunks = embeddings.chunk_text(doc.extracted_text)
    if chunks:
        vectors = embeddings.embed_texts(chunks)
        for i, (t, v) in enumerate(zip(chunks, vectors)):
            s.add(DocumentChunk(document_id=doc.id, chunk_index=i, text=t, embedding=v))
    s.commit()
    return len(chunks)


def _cosine(a, b):
    return sum(x * y for x, y in zip(a, b))   # vector আগে থেকেই normalize করা


def semantic_search(s, query, limit=10):
    """সবচেয়ে কাছের chunk, প্রতি document-এর সেরাটা। ফেরত: [(document_id, score, snippet)]"""
    qv = embeddings.embed_query(query)
    if s.bind.dialect.name == "postgresql":
        rows = s.execute(sql(
            "SELECT document_id, 1 - (embedding <=> CAST(:q AS vector)) AS score, text "
            "FROM document_chunks ORDER BY embedding <=> CAST(:q AS vector) LIMIT :n"),
            {"q": str(qv), "n": limit * 5}).all()
        scored = [(r.document_id, float(r.score), r.text) for r in rows]
    else:  # SQLite (test)
        scored = [(c.document_id, _cosine(qv, c.embedding), c.text)
                  for c in s.scalars(select(DocumentChunk))]
        scored.sort(key=lambda x: -x[1])
    best = {}
    for doc_id, score, text in scored:
        if doc_id not in best:
            best[doc_id] = (doc_id, score, text[:200])
    return list(best.values())[:limit]


def keyword_ids(s, query, limit=50):
    like = f"%{query}%"
    q = (select(Document.id)
         .where(Document.file_name.ilike(like) | Document.invoice_key.ilike(like)
                | Document.extracted_text.ilike(like))
         .order_by(Document.id.desc()).limit(limit))
    return list(s.scalars(q))


def hybrid_search(s, query, limit=10):
    """keyword আর semantic ফল মেলায় (Reciprocal Rank Fusion)।"""
    sem = semantic_search(s, query, limit=limit * 2)
    kw = keyword_ids(s, query, limit=limit * 2)
    scores, snippets = {}, {d: sn for d, _, sn in sem}
    for rank, (d, _, _) in enumerate(sem):
        scores[d] = scores.get(d, 0) + 1 / (60 + rank)
    for rank, d in enumerate(kw):
        scores[d] = scores.get(d, 0) + 1 / (60 + rank)
    top = sorted(scores.items(), key=lambda x: -x[1])[:limit]
    return [(d, sc, snippets.get(d)) for d, sc in top]