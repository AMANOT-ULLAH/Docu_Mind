import pytesseract
from PIL import Image, ImageOps, ImageFilter

def preprocess(img: Image.Image) -> Image.Image:
    img = ImageOps.exif_transpose(img)      # ফোনে তোলা ছবির ঘোরানো ঠিক করে
    img = ImageOps.grayscale(img)           # রঙ বাদ
    img = ImageOps.autocontrast(img)        # ঝাপসা/ফ্যাকাশে ছবির contrast বাড়ায়
    if min(img.size) < 1000:                # ছোট ছবি হলে বড় করি, OCR-এর জন্য ভালো
        img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
    img = img.filter(ImageFilter.MedianFilter(3))   # ছোট noise কমায়
    return img

def ocr_image(img: Image.Image, lang: str = "eng+ben"):
    """text আর গড় confidence (0-100) ফেরত দেয়।"""
    processed = preprocess(img)
    text = pytesseract.image_to_string(processed, lang=lang).strip()
    data = pytesseract.image_to_data(
        processed, lang=lang, output_type=pytesseract.Output.DICT
    )
    confs = [float(c) for w, c in zip(data["text"], data["conf"])
             if w.strip() and float(c) >= 0]
    confidence = round(sum(confs) / len(confs), 1) if confs else 0.0
    return text, confidence