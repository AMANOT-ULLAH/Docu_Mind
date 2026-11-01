import resource
import sys
import time
from io import BytesIO
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "backend"))
from app.processors.router import process_document  # noqa: E402

OUT = HERE / "dataset_big"
OUT.mkdir(exist_ok=True)


def page_lines(i):
    lines = ["ABC Trading Ltd", f"Invoice No: INV-BIG-{i:04d}", "Date: 15 October 2026",
             "Bill To: XYZ Corporation"]
    lines += [f"Item {k} description text   {k} x {100 + k} = {k * (100 + k)}" for k in range(1, 26)]
    lines += ["Subtotal: 10,000", "VAT (10%): 1,000", "Total: 11,000 BDT"]
    return lines


def make_digital(n, path):
    doc = pymupdf.open()
    for i in range(1, n + 1):
        p = doc.new_page(width=595, height=842)
        y = 60
        for t in page_lines(i):
            p.insert_text((50, y), t, fontsize=11)
            y += 22
    doc.save(path)
    doc.close()


def make_scanned(n, path):
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
    doc = pymupdf.open()
    for i in range(1, n + 1):
        im = Image.new("RGB", (1240, 1754), "white")
        d = ImageDraw.Draw(im)
        y = 100
        for t in page_lines(i):
            d.text((80, y), t, font=font, fill="black")
            y += 48
        buf = BytesIO()
        im.save(buf, "JPEG", quality=60)
        page = doc.new_page(width=595, height=842)
        page.insert_image(page.rect, stream=buf.getvalue())
    doc.save(path)
    doc.close()


def measure(path):
    t = time.perf_counter()
    doc = process_document(str(path))
    secs = time.perf_counter() - t
    chars = sum(len(p.text) for p in doc.pages)
    print(f"file:            {path.name} ({path.stat().st_size / 1e6:.1f} MB)")
    print(f"status:          {doc.status}, pages read: {len(doc.pages)}")
    print(f"processing:      {secs:.1f} s  ({secs / max(1, len(doc.pages)):.3f} s/page)")
    print(f"peak memory:     {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.0f} MB")
    print(f"extracted text:  {chars:,} chars  (~{chars // 4:,} tokens, rough chars/4 estimate)")
    print(f"errors/warnings: {doc.errors} {doc.warnings}")


if __name__ == "__main__":
    mode, n = sys.argv[1], int(sys.argv[2])
    path = OUT / f"{mode}_{n}.pdf"
    t = time.perf_counter()
    (make_digital if mode == "digital" else make_scanned)(n, path)
    print(f"generated {path.name} in {time.perf_counter() - t:.1f} s")
    measure(path)