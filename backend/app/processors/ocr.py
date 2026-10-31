import pytesseract
from PIL import Image, ImageOps, ImageFilter

LOW_WORD_CONF = 60      # এর নিচে confidence হলে শব্দটা "সন্দেহজনক"
TESSERACT_CONFIG = "--psm 4"   # লাইন ধরে পড়ে, table-এর সরু কলাম ফেলে দেয় না


def preprocess(img: Image.Image) -> Image.Image:
    img = ImageOps.exif_transpose(img)      # ফোনে তোলা ছবির ঘোরানো ঠিক করে
    img = ImageOps.grayscale(img)
    img = ImageOps.autocontrast(img)
    if min(img.size) < 1000:                # ছোট ছবি বড় করি
        img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
    img = img.filter(ImageFilter.MedianFilter(3))
    return img


def _run(processed, lang):
    """একবার OCR চালিয়ে (text, গড় confidence, সন্দেহজনক শব্দের %) ফেরত দেয়।"""
    data = pytesseract.image_to_data(
        processed, lang=lang, config=TESSERACT_CONFIG,
        output_type=pytesseract.Output.DICT,
    )
    lines, confs = {}, []
    for i, word in enumerate(data["text"]):
        if not word.strip():
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append(word)
        c = float(data["conf"][i])
        if c >= 0:
            confs.append(c)
    text = "\n".join(" ".join(words) for words in lines.values())
    if not confs:
        return text, 0.0, 100.0
    avg = round(sum(confs) / len(confs), 1)
    low = round(100 * sum(1 for c in confs if c < LOW_WORD_CONF) / len(confs), 1)
    return text, avg, low


def ocr_image(img: Image.Image, lang: str = "eng+ben"):
    """lang 'eng+ben' হলে আগে শুধু 'eng' চালাই। ফল ভালো হলে থামি (দ্রুত আর পরিষ্কার);
    খারাপ হলে 'eng+ben' চালিয়ে দুটোর ভালোটা নিই।"""
    processed = preprocess(img)
    if "+" not in lang:
        return _run(processed, lang)
    first = lang.split("+")[0]
    text, avg, low = _run(processed, first)
    if avg >= 85 and low <= 10:          # এই দুটো সংখ্যা আমার অনুমান, আসল data দিয়ে tune করব
        return text, avg, low
    t2, a2, l2 = _run(processed, lang)
    return (t2, a2, l2) if a2 > avg else (text, avg, low)