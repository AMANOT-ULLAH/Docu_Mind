import io
import pymupdf
from PIL import Image
from .ocr import ocr_image
from .schemas import PageResult

MIN_TEXT_CHARS = 30  # এর কম text থাকলে page-টাকে scanned ধরব

def extract_pdf_pages(path, ocr_lang="eng+ben", dpi=200):
    pages, warnings = [], []
    doc = pymupdf.open(path)  # নষ্ট PDF হলে এখানে error আসবে
    for i, page in enumerate(doc, start=1):
        try:
            text = page.get_text().strip()
            if len(text) >= MIN_TEXT_CHARS:
                pages.append(PageResult(page_number=i, method="digital", text=text))
                continue
            # text নেই = scanned page, তাই ছবি বানিয়ে OCR
            pix = page.get_pixmap(dpi=dpi)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text, conf, low = ocr_image(img, ocr_lang)
            pages.append(PageResult(page_number=i, method="ocr", text=text,
                                    confidence=conf, low_conf_words=low))
        except Exception as e:
            warnings.append(f"page {i} failed: {e}")
    doc.close()
    return pages, warnings