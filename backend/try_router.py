from pathlib import Path
from app.processors.router import process_document

folder = Path("../evaluation/sample_data")
rows = []
for f in sorted(folder.iterdir()):
    r = process_document(f)
    err = r.errors[0][:60] if r.errors else ""
    rows.append((r.file_name, r.file_type, r.status, len(r.pages), r.processing_seconds, err))
    print(f"{r.file_name:22} {r.file_type:8} {r.status:8} pages={len(r.pages):<3} {r.processing_seconds:>6}s  {err}")

total = len(rows)
ok = sum(1 for r in rows if r[2] == "success")
print(f"\nTotal: {total} | success: {ok} | partial: {sum(1 for r in rows if r[2]=='partial')} | failed: {sum(1 for r in rows if r[2]=='failed')}")