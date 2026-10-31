import time
from app.extraction.llm_extractor import _call_gemini, _parse, verify_evidence

FULL = """INVOICE NO: INV-2026-102
DATE: 15 OCT 2026
SUPPLIER: ABC Limited
CUSTOMER: XYZ Corporation
Product A: 2 x 1000 = 2000
Product B: 3 x 1500 = 4500
Subtotal: 6500
Tax: 650
Total: 7150
Currency: BDT"""

NO_TAX = """INVOICE NO: INV-2026-103
SUPPLIER: ABC Limited
CUSTOMER: XYZ Corporation
Product A: 2 x 1000 = 2000
Total: 2000"""

MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.5-flash"]

for model in MODELS:
    print("=" * 10, model)
    for label, text in [("FULL", FULL), ("NO_TAX", NO_TAX)]:
        try:
            t = time.perf_counter()
            r = _parse(_call_gemini(model, text))
            secs = time.perf_counter() - t
            flags = verify_evidence(r, text)
            if label == "FULL":
                ok = (r.invoice_number.value == "INV-2026-102"
                      and r.invoice_date.value == "2026-10-15"
                      and r.total.value == 7150 and len(r.line_items) == 2)
            else:
                # যা document-এ নেই, তা অবশ্যই null হতে হবে
                ok = all(f.value is None for f in
                         [r.invoice_date, r.subtotal, r.tax, r.currency])
            print(f"{label:7} {secs:5.1f}s  correct={ok}  evidence_flags={flags}")
        except Exception as e:
            print(f"{label:7} FAIL {type(e).__name__}: {str(e)[:100]}")
        time.sleep(2)