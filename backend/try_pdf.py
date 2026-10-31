from app.processors.pdf_processor import extract_pdf_pages

pages, warns = extract_pdf_pages("../evaluation/sample_data/test.pdf")
for p in pages[:3]:
    print(p.page_number, p.method, "|", p.text[:150])
print("total pages:", len(pages))
print("warnings:", warns)