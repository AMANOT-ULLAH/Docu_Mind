import copy

from app.db import crud
from app.db.models import ProcessingEvent, ValidationIssue
from app.validation.duplicates import find_duplicates, invoice_key
from app.validation.invoice_validator import validate_invoice

SCALAR_FIELDS = ["invoice_number", "invoice_date", "supplier_name", "customer_name",
                 "subtotal", "tax", "total", "currency"]
NUMERIC = {"subtotal", "tax", "total"}


def apply_correction(s, doc, fields, line_items=None):
    """
    মানুষের সংশোধন `extraction.corrected`-এ রাখে (AI-র মূল উত্তর `result` অক্ষত থাকে),
    তারপর সংশোধিত ডেটা দিয়ে validation ও duplicate যাচাই আবার চালায়।
    """
    e = doc.extraction
    if e is None:
        raise ValueError("document has no extraction to correct")
    if not fields and line_items is None:
        raise ValueError("nothing to correct")
    unknown = set(fields) - set(SCALAR_FIELDS)
    if unknown:
        raise ValueError(f"unknown field(s): {', '.join(sorted(unknown))}")

    corrected = copy.deepcopy(e.corrected or e.result)
    for k, v in fields.items():
        if v is not None:
            if k in NUMERIC:
                if isinstance(v, bool) or not isinstance(v, (int, float)):
                    raise ValueError(f"{k} must be a number")
            else:
                v = str(v)
        corrected[k] = {"value": v, "evidence": "manual correction", "confidence": "high"}
    if line_items is not None:
        corrected["line_items"] = [{**li, "evidence": "manual correction"} for li in line_items]
    corrected["notes"] = []   # মডেলের অনিশ্চয়তার নোট মানুষ দেখে নিয়েছে

    issues = validate_invoice(corrected)["issues"]
    key = invoice_key(corrected)
    issues += find_duplicates(doc.file_hash, key, crud.known_records(s, exclude_id=doc.id))

    e.corrected = corrected
    doc.invoice_key = key
    doc.issues.clear()
    s.flush()
    for i in issues:
        doc.issues.append(ValidationIssue(
            type=i["type"], field=i["field"], severity=i["severity"],
            message=i["message"], expected=i["expected"], actual=i["actual"]))
    doc.review_reasons = [f"{i['type']}: {i['field']}" for i in issues]
    doc.needs_review = bool(issues)
    what = ", ".join(sorted(fields)) + (" +line_items" if line_items is not None else "")
    doc.events.append(ProcessingEvent(event="corrected", message=what.strip(", ")))
    s.commit()
    return doc