import json
from app.extraction.llm_extractor import extract_invoice, verify_evidence

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

for name, text in [("FULL", FULL), ("NO_TAX_NO_DATE", NO_TAX)]:
    print("=" * 20, name)
    result, meta = extract_invoice(text)
    flags = verify_evidence(result, text)
    print("answered by:", meta["provider"], meta["model"])
    print("failed before that:", meta["attempts"])
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
    print("evidence flags:", flags)