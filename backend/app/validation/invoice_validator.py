import re
from decimal import Decimal, InvalidOperation

TOLERANCE = Decimal("0.01")     # rounding-এর সামান্য ফারাক মেনে নিই
REQUIRED = ["invoice_number", "invoice_date", "supplier_name", "total"]
FIELDS = ["invoice_number", "invoice_date", "supplier_name",
          "customer_name", "subtotal", "tax", "total", "currency"]
KNOWN_CURRENCIES = {"BDT", "USD", "EUR", "GBP", "INR", "AED", "SAR",
                    "JPY", "CNY", "AUD", "CAD", "SGD", "MYR"}
INVOICE_NO_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-/_.#]*$")
AMBIGUOUS_DECIMAL_RE = re.compile(r"\d\.\d{3}(?!\d)")   # যেমন 7.050


def _d(x):
    """float থেকে সরাসরি না গিয়ে str দিয়ে Decimal, যাতে 0.1+0.2 ধরনের ভুল না হয়।"""
    if x is None:
        return None
    try:
        return Decimal(str(x))
    except InvalidOperation:
        return None


def _close(a, b):
    return abs(a - b) <= TOLERANCE


def validate_invoice(ex: dict) -> dict:
    issues = []

    def add(type_, field, message, expected=None, actual=None, severity="error"):
        issues.append({
            "type": type_, "field": field, "severity": severity, "message": message,
            "expected": None if expected is None else str(expected),
            "actual": None if actual is None else str(actual),
        })

    # 1. দরকারি field নেই
    for f in REQUIRED:
        if ex[f]["value"] is None:
            add("missing_field", f, f"{f} is missing")

    # 2. ফরম্যাট সন্দেহজনক (OCR-ভুলের লক্ষণ)
    no = ex["invoice_number"]["value"]
    if no and not INVOICE_NO_RE.match(no):
        add("suspicious_format", "invoice_number",
            "contains spaces or unusual characters (possible OCR error)", actual=no)
    cur = ex["currency"]["value"]
    if cur and cur.upper() not in KNOWN_CURRENCIES:
        add("unknown_currency", "currency",
            "not a recognised currency code (possible OCR error)", actual=cur)

    # 3. সংখ্যা ও হিসাব
    sub, tax, total = (_d(ex[k]["value"]) for k in ("subtotal", "tax", "total"))
    for name, v in (("subtotal", sub), ("tax", tax), ("total", total)):
        if v is not None and v < 0:
            add("negative_value", name, f"{name} is negative", actual=v)

    for name in ("subtotal", "tax", "total"):
        ev = ex[name]["evidence"]
        if ex[name]["value"] is not None and ev and AMBIGUOUS_DECIMAL_RE.search(ev):
            add("ambiguous_number", name,
                                "dot followed by exactly 3 digits (e.g. 7.050 could mean 7.05 or 7,050); verify manually",
                actual=ex[name]["value"], severity="warning")

    amounts, items = [], ex["line_items"]
    for i, it in enumerate(items, start=1):
        q, p, a = _d(it["quantity"]), _d(it["unit_price"]), _d(it["amount"])
        if None not in (q, p, a) and not _close(q * p, a):
            add("line_item_mismatch", f"line_items[{i}]",
                "quantity x unit price != amount", expected=q * p, actual=a)
        if a is not None:
            amounts.append(a)

    if items and len(amounts) == len(items) and sub is not None:
        s = sum(amounts)
        if not _close(s, sub):
            add("subtotal_mismatch", "subtotal",
                "sum of line items != subtotal", expected=s, actual=sub)

    if sub is not None and total is not None:
        if tax is not None:
            if not _close(sub + tax, total):
                add("total_mismatch", "total", "subtotal + tax != total",
                    expected=sub + tax, actual=total)
        elif not _close(sub, total):
            add("total_mismatch", "total",
                "total differs from subtotal but no tax value was found",
                expected=sub, actual=total)

    # 4. model নিজে যা সন্দেহ করেছে
    for f in FIELDS:
        if ex[f]["value"] is not None and ex[f]["confidence"] == "low":
            add("low_confidence", f, "model reported low confidence", severity="warning")
    for note in ex["notes"]:
        add("model_note", "notes", note, severity="warning")

    return {"status": "review_required" if issues else "ok", "issues": issues}