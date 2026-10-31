import hashlib
import re


def file_hash(path) -> str:
    """ফাইলের SHA-256। একই ফাইল দুইবার upload হলে মিলবে।"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _norm(s):
    """ছোট হাতের অক্ষর, শুধু অক্ষর-সংখ্যা। স্পেস, ড্যাশ, ' ইত্যাদি বাদ।"""
    if s is None:
        return None
    s = re.sub(r"[^a-z0-9]", "", str(s).lower())
    return s or None


def invoice_key(ex: dict):
    """invoice number + supplier + date থেকে একটা key। তিনটার একটাও না থাকলে None।"""
    parts = (_norm(ex["invoice_number"]["value"]),
             _norm(ex["supplier_name"]["value"]),
             _norm(ex["invoice_date"]["value"]))
    if None in parts:
        return None
    return "|".join(parts)


def find_duplicates(fhash, key, known) -> list:
    """
    known: আগে প্রসেস হওয়া রেকর্ডের তালিকা,
           প্রতিটা {"id": ..., "file_hash": ..., "key": ...}
    ফেরত দেয় validator-এর মতো একই ছাঁচের issue তালিকা।
    """
    issues = []
    for rec in known:
        if fhash and rec.get("file_hash") == fhash:
            issues.append({
                "type": "duplicate_file", "field": "file", "severity": "error",
                "message": f"identical file already processed (id: {rec['id']})",
                "expected": None, "actual": str(rec["id"]),
            })
        elif key and rec.get("key") == key:
            issues.append({
                "type": "duplicate_invoice", "field": "invoice_number", "severity": "error",
                "message": "same invoice number, supplier and date already exists "
                           f"(id: {rec['id']})",
                "expected": None, "actual": str(rec["id"]),
            })
    return issues