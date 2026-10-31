import time
from app.validation.invoice_validator import validate_invoice
from app.processors.router import process_document
from app.extraction.llm_extractor import (extract_invoice, verify_evidence,
                                          AllProvidersFailed)

LOW_OCR_CONFIDENCE = 60
LOW_WORD_RATIO = 15   # শতাংশ

def build_text(doc) -> str:
    """সব page-এর text একসাথে জোড়ে, প্রতিটার আগে page চিহ্ন দিয়ে।"""
    return "\n\n".join(
        f"--- PAGE {p.page_number} ({p.method}) ---\n{p.text}" for p in doc.pages
    )


def process_and_extract(path) -> dict:
    start = time.perf_counter()
    doc = process_document(path)
    out = {
        "file": doc.file_name,
        "doc_status": doc.status,
        "extraction": None,
        "provider": None,
        "evidence_flags": [],
        "review_reasons": [],
        "errors": list(doc.errors),
    }

    if doc.status == "failed":
        out["review_reasons"].append("document could not be processed")
        out["seconds"] = round(time.perf_counter() - start, 2)
        return out

        for p in doc.pages:
            if p.method != "ocr":
                continue
            if p.confidence is not None and p.confidence < LOW_OCR_CONFIDENCE:
                out["review_reasons"].append(f"page {p.page_number}: low OCR confidence ({p.confidence})")
            if p.low_conf_words is not None and p.low_conf_words > LOW_WORD_RATIO:
                out["review_reasons"].append(
                    f"page {p.page_number}: {p.low_conf_words}% of words have low OCR confidence")

    text = build_text(doc)
    try:
        result, meta = extract_invoice(text)
    except AllProvidersFailed as e:
        out["review_reasons"].append("all LLM providers failed")
        out["errors"].append(str(e)[:300])
        out["seconds"] = round(time.perf_counter() - start, 2)
        return out

    flags = verify_evidence(result, text)
    out["evidence_flags"] = flags
    if flags:
        out["review_reasons"].append("evidence not found in source text")
    out["extraction"] = result.model_dump()
    out["validation"] = validate_invoice(out["extraction"])
    out["review_reasons"] += [
        f"{i['type']}: {i['field']}" for i in out["validation"]["issues"]
    ]
    out["provider"] = f"{meta['provider']}/{meta['model']}"
    out["seconds"] = round(time.perf_counter() - start, 2)
    return out