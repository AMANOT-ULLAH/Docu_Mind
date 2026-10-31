from PIL import Image, ImageSequence
from .ocr import ocr_image
from .schemas import PageResult

LOW_CONFIDENCE = 60   # এর নিচে হলে warning

def extract_image_pages(path, lang="eng+ben"):
    pages, warnings = [], []

    # ছবিটা সত্যিই পড়া যায় কি না আগে দেখি (corrupted file ধরার জন্য)
    try:
        with Image.open(path) as probe:
            probe.verify()
    except Exception as e:
        raise ValueError(f"Corrupted or unreadable image: {e}")

    img = Image.open(path)   # verify()-এর পর আবার খুলতে হয়
    for i, frame in enumerate(ImageSequence.Iterator(img), start=1):  # TIFF-এর একাধিক frame
        try:
            text, conf, low = ocr_image(frame.copy(), lang)
            if not text:
                warnings.append(f"frame {i}: no text found")
            elif conf < LOW_CONFIDENCE or low > 15:
                warnings.append(f"frame {i}: low OCR quality (avg {conf}, {low}% doubtful words)")
            pages.append(PageResult(page_number=i, method="ocr", text=text,
                                    confidence=conf, low_conf_words=low))
        except Exception as e:
            warnings.append(f"frame {i} failed: {e}")
    return pages, warnings