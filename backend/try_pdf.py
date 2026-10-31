import sys
from app.processors.pdf_processor import extract_pdf_pages

path = sys.argv[1] if len(sys.argv) > 1 else "../evaluation/sample_data/test.pdf"
pages, warns = extract_pdf_pages(path)
for p in pages[:3]:
    print(p.page_number, p.method, "conf:", p.confidence, "|", p.text[:120].replace("\n", " "))
print("total pages:", len(pages))
print("warnings:", warns)