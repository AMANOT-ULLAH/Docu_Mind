import io
from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore, Lock

import pymupdf
from PIL import Image

from app.config import OCR_WORKERS
from .ocr import ocr_image
from .schemas import PageResult

MIN_TEXT_CHARS = 30  # এর কম text থাকলে page-টাকে scanned ধরব


def _ocr_page(i, img, lang):
    """একটা পেজের OCR। কখনো exception ছোঁড়ে না, (ফল, error) ফেরত দেয়।"""
    try:
        text, conf, low = ocr_image(img, lang)
        page = PageResult(page_number=i, method="ocr", text=text,
                          confidence=conf, low_conf_words=low)
        return page, None
    except Exception as e:
        return None, f"page {i} failed: {e}"
    finally:
        img.close()


def extract_pdf_pages(path, ocr_lang="eng+ben", dpi=200, workers=None, progress=None):
    """progress(done, total) যেকোনো thread থেকে ডাকা হতে পারে, তাই হালকা ও thread-safe রাখতে হবে।"""
    workers = OCR_WORKERS if workers is None else workers
    results, warnings = {}, []
    doc = pymupdf.open(path)  # নষ্ট PDF হলে এখানে error আসবে
    total = len(doc)
    state = {"done": 0}
    lock = Lock()

    def tick():
        with lock:
            state["done"] += 1
            n = state["done"]
        if progress:
            try:
                progress(n, total)
            except Exception:
                pass  # progress-এর ভুলে প্রসেসিং নষ্ট হবে না

    if progress:
        try:
            progress(0, total)   # শুরুতেই মোট পেজ জানাই
        except Exception:
            pass

    pool = ThreadPoolExecutor(max_workers=workers) if workers > 1 else None
    slots = BoundedSemaphore(workers * 2) if pool else None
    futures = []
    try:
        for i, page in enumerate(doc, start=1):
            try:
                text = page.get_text().strip()
                if len(text) >= MIN_TEXT_CHARS:
                    results[i] = PageResult(page_number=i, method="digital", text=text)
                    tick()
                    continue
                # text নেই = scanned page, তাই ছবি বানিয়ে OCR
                pix = page.get_pixmap(dpi=dpi)
                if pix.n == 3:
                    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                else:
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
            except Exception as e:
                warnings.append(f"page {i} failed: {e}")
                tick()
                continue

            if pool is None:
                res, err = _ocr_page(i, img, ocr_lang)
                if res:
                    results[i] = res
                else:
                    warnings.append(err)
                tick()
            else:
                slots.acquire()   # একসাথে সীমিত সংখ্যক ছবি memory-তে
                fut = pool.submit(_ocr_page, i, img, ocr_lang)
                fut.add_done_callback(lambda f: (slots.release(), tick()))
                futures.append(fut)

        for fut in futures:
            res, err = fut.result()
            if res:
                results[res.page_number] = res
            else:
                warnings.append(err)
    finally:
        if pool:
            pool.shutdown(wait=True)
        doc.close()

    pages = [results[k] for k in sorted(results)]
    return pages, warnings