from app.services.pipeline import process_and_extract

FILES = ["inv_digital.pdf", "inv_scanned.pdf", "inv_photo.jpg", "inv_notax.pdf"]

for name in FILES:
    r = process_and_extract("../evaluation/sample_data/" + name)
    print("=" * 60)
    print(name, "| doc:", r["doc_status"], "|", r["provider"], "|", r["seconds"], "s")
    ex = r["extraction"]
    if ex:
        for k in ["invoice_number", "invoice_date", "supplier_name",
                  "customer_name", "subtotal", "tax", "total", "currency"]:
            print(f"  {k:15} {ex[k]['value']!r:28} [{ex[k]['confidence']}]  <- {ex[k]['evidence']!r}")
        print("  line items:", len(ex["line_items"]))
        print("  notes:", ex["notes"])

    v = r.get("validation")
    if v:
        print("  validation:", v["status"])
        for i in v["issues"]:
            print(f"    [{i['severity']}] {i['type']} ({i['field']}): {i['message']}")
    
    print("  review:", r["review_reasons"], "| flags:", r["evidence_flags"])
    if r["errors"]:
        print("  errors:", r["errors"])