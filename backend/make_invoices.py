import pymupdf
from PIL import Image, ImageFilter

OUT = "../evaluation/sample_data/"


def build_invoice_pdf(path, number, date, customer, items, tax=None, currency="BDT"):
    doc = pymupdf.open()
    page = doc.new_page()
    y = 70
    def line(text, x=60, size=11):
        nonlocal y
        page.insert_text((x, y), text, fontsize=size)
        y += 20

    line("ABC Trading Ltd", size=16)
    line("House 12, Road 5, Dhanmondi, Dhaka")
    y += 10
    line("INVOICE", size=14)
    line(f"Invoice No: {number}")
    line(f"Date: {date}")
    line(f"Bill To: {customer}")
    y += 15
    page.insert_text((60, y), "Description", fontsize=11)
    page.insert_text((280, y), "Qty", fontsize=11)
    page.insert_text((340, y), "Unit Price", fontsize=11)
    page.insert_text((450, y), "Amount", fontsize=11)
    y += 20
    subtotal = 0
    for desc, qty, price in items:
        amount = qty * price
        subtotal += amount
        page.insert_text((60, y), desc, fontsize=11)
        page.insert_text((280, y), str(qty), fontsize=11)
        page.insert_text((340, y), f"{price:,}", fontsize=11)
        page.insert_text((450, y), f"{amount:,}", fontsize=11)
        y += 20
    y += 10
    line(f"Subtotal: {subtotal:,}", x=380)
    if tax is not None:
        line(f"VAT (10%): {tax:,}", x=380)
        line(f"Total: {subtotal + tax:,} {currency}", x=380)
    else:
        line(f"Total: {subtotal:,} {currency}", x=380)
    doc.save(path)
    doc.close()


def rasterize_pdf(src, dst, dpi=150):
    s = pymupdf.open(src)
    out = pymupdf.open()
    for p in s:
        pix = p.get_pixmap(dpi=dpi)
        np = out.new_page(width=p.rect.width, height=p.rect.height)
        np.insert_image(np.rect, pixmap=pix)
    out.save(dst)


items = [("Laptop stand", 2, 1500), ("USB-C cable", 5, 300), ("Wireless mouse", 3, 850)]

build_invoice_pdf(OUT + "inv_digital.pdf", "INV-2026-1025", "15 October 2026",
                  "XYZ Corporation", items, tax=705)

rasterize_pdf(OUT + "inv_digital.pdf", OUT + "inv_scanned.pdf")        # শুধু ছবি-PDF

pix = pymupdf.open(OUT + "inv_digital.pdf")[0].get_pixmap(dpi=150)    # খারাপ মানের ছবি
img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples).convert("L")
img = img.resize((img.width // 2, img.height // 2)).filter(ImageFilter.GaussianBlur(0.8))
img = img.rotate(1.5, expand=True, fillcolor=255)
img.save(OUT + "inv_photo.jpg", quality=35)

build_invoice_pdf(OUT + "inv_notax.pdf", "INV-2026-1026", "20 October 2026",
                  "Rahman Traders", [("Printer paper", 10, 450)], tax=None)
print("done")