import sys
from app.processors.image_processor import extract_image_pages

pages, warns = extract_image_pages(sys.argv[1])
for p in pages:
    print(p.page_number, p.method, "conf:", p.confidence, "|", p.text[:100].replace("\n", " "))
print("warnings:", warns)