import math

from google import genai
from google.genai import types

from app import config

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def normalize(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n else list(v)


def chunk_text(text, size=1500, overlap=200):
    """বড় text (১০০০ পেজ পর্যন্ত) ছোট টুকরোয় ভাঙে। টুকরোর মাঝে সামান্য overlap থাকে।"""
    text = (text or "").strip()
    if not text:
        return []
    chunks, i = [], 0
    while i < len(text):
        chunks.append(text[i:i + size])
        i += size - overlap
    return chunks


def embed_texts(texts, task="RETRIEVAL_DOCUMENT", batch=50):
    """text-এর তালিকা -> normalize করা vector-এর তালিকা।"""
    out = []
    for i in range(0, len(texts), batch):
        r = _get_client().models.embed_content(
            model=config.EMBED_MODEL,
            contents=texts[i:i + batch],
            config=types.EmbedContentConfig(
                task_type=task, output_dimensionality=config.EMBED_DIM))
        out += [normalize(e.values) for e in r.embeddings]
    return out


def embed_query(q):
    return embed_texts([q], task="RETRIEVAL_QUERY")[0]