import pymupdf
from PIL import Image, ImageFilter

out = "../evaluation/sample_data/"
doc = pymupdf.open(out + "test.pdf")

def to_pil(page, dpi=150):
    pix = page.get_pixmap(dpi=dpi)
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

img = to_pil(doc[0])
img.save(out + "page1.png")                       # পরিষ্কার PNG

poor = img.convert("L")                           # খারাপ মানের নকল: ছোট + ঝাপসা + একটু বাঁকা + কম quality
poor = poor.resize((poor.width // 3, poor.height // 3)).filter(ImageFilter.GaussianBlur(1.2))
poor = poor.rotate(2, expand=True, fillcolor=255)
poor.save(out + "page1_poor.jpg", quality=30)

frames = [to_pil(p) for p in doc]                 # 3 frame-এর TIFF
frames[0].save(out + "multi.tiff", save_all=True, append_images=frames[1:])
print("done")