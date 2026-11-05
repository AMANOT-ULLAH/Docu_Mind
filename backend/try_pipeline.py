from app.services.pipeline import process_and_extract

FILES = ["inv_digital.pdf", "inv_scanned.pdf", "inv_photo.jpg", "inv_notax.pdf",
         "inv_digital.pdf"]
known = []

FIELDS = ["invoice_number", "invoice_date", "supplier_name",
          "customer_name", "subtotal", "tax", "total", "currency"]

for name in FILES:
    print("=" * 60)
    try:
        r = process_and_extract("../evaluation/sample_data/" + name, known=known)
    except Exception as e:
        print(name, "| CRASHED:", type(e).__name__, e)
        continue

    print(name, "| doc:", r["doc_status"], "|", r["provider"], "|", r["seconds"], "s")
    print("  time: file", r.get("file_seconds"), "s | LLM", r.get("llm_seconds"), "s")

    ex = r["extraction"]
    if ex:
        for k in FIELDS:
            print(f"  {k:15} {ex[k]['value']!r:28} [{ex[k]['confidence']}]  <- {ex[k]['evidence']!r}")
        print("  line items:", len(ex["line_items"]))
        print("  notes:", ex["notes"])

    v = r.get("validation")
    if v:
        print("  validation:", v["status"])
        for i in v["issues"]:
            print(f"    [{i['severity']}] {i['type']} ({i['field']}): {i['message']}")

    known.append({"id": f"{name}#{len(known)+1}",
                  "file_hash": r["file_hash"], "key": r["invoice_key"]})       
    
    print("  review:", r["review_reasons"], "| flags:", r["evidence_flags"])
    if r["errors"]:
        print("  errors:", r["errors"])
        