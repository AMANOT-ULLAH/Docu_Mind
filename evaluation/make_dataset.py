"""Evaluation dataset: ফাইল + labels.json (ground truth)। চালাও: python make_dataset.py"""
import csv
import io
import json
import shutil
from datetime import date
from functools import lru_cache
from pathlib import Path
import random

import numpy as np
import openpyxl
import pymupdf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).parent / "dataset"
W, H = 1240, 1754

SUPPLIERS = [
    ("Dhaka Office Supplies Ltd", "Plot 8, Road 11, Banani, Dhaka"),
    ("Padma Electronics Ltd", "45 Agrabad C/A, Chattogram"),
    ("Meghna Stationery House", "12 Zindabazar, Sylhet"),
    ("Jamuna Hardware Traders", "88 Station Road, Rajshahi"),
    ("Surma Tech Solutions", "7 Sher-e-Bangla Road, Khulna"),
]
CUSTOMERS = ["Karim Enterprises", "Rahman Traders", "Nova Trading Co", "Green Valley School",
             "Alpha Clinic", "Sunrise Bakery", "City Pharmacy"]
CUST_ADDR = "House 4, Road 2, Mirpur, Dhaka"
CATALOG_BDT = [("Office chair", 6500), ("Standing desk", 12000), ("Whiteboard", 1800),
               ("Laptop stand", 1500), ("USB-C cable", 300), ("Printer paper box", 900),
               ("Desk lamp", 1200), ("Wireless keyboard", 2100)]
CATALOG_USD = [("Cloud hosting plan", 120.00), ("Domain renewal", 14.50),
               ("SSL certificate", 89.90), ("Support hours", 45.25), ("Backup storage", 19.99)]


# ---------- ডেটা ----------
def finish(inv, rate):
    inv["subtotal"] = round(sum(i["amount"] for i in inv["items"]), 2)
    if rate is None:
        inv["tax_rate"], inv["tax"], inv["total"] = None, None, inv["subtotal"]
    else:
        inv["tax_rate"] = rate
        inv["tax"] = round(inv["subtotal"] * rate / 100, 2)
        inv["total"] = round(inv["subtotal"] + inv["tax"], 2)


def build(idx, currency="BDT", with_tax=True):
    r = random.Random(1000 + idx)
    sup_name, sup_addr = SUPPLIERS[idx % len(SUPPLIERS)]
    catalog = CATALOG_USD if currency == "USD" else CATALOG_BDT
    items = []
    for desc, price in r.sample(catalog, r.randint(2, 4)):
        q = r.randint(1, 9)
        items.append({"description": desc, "quantity": q, "unit_price": price,
                      "amount": round(q * price, 2)})
    inv = {"invoice_number": f"INV-2026-{3000 + idx}",
           "invoice_date": date(2026, 10, 1 + idx % 28).isoformat(), "date_style": idx % 3,
           "supplier_name": sup_name, "supplier_addr": sup_addr,
           "customer_name": CUSTOMERS[(idx * 3 + 1) % len(CUSTOMERS)],
           "currency": currency, "items": items}
    finish(inv, r.choice([5, 10, 15]) if with_tax else None)
    return inv


def fmt_date(inv):
    d = date.fromisoformat(inv["invoice_date"])
    return [d.strftime("%d %B %Y"), d.isoformat(), d.strftime("%d/%m/%Y")][inv["date_style"]]


def m(x, inv):
    if inv["currency"] == "USD":
        return f"{x:,.2f}"
    return f"{int(x):,}" if abs(x - round(x)) < 1e-9 else f"{x:,.2f}"


def truth(inv):
    return {k: inv[k] for k in ("invoice_number", "invoice_date", "supplier_name",
                                "customer_name", "subtotal", "tax", "total", "currency")} | {
        "line_items": [{k: i[k] for k in ("description", "quantity", "unit_price", "amount")}
                       for i in inv["items"]]}


# ---------- পাতার নকশা (ছবি আর PDF একই নকশা ব্যবহার করে) ----------
def layout(inv):
    L = []

    def add(t, x, y, s=28, b=False, a="l"):
        L.append((t, x, y, s, b, a))

    add(inv["supplier_name"], 80, 80, 44, True)
    add(inv["supplier_addr"], 80, 140, 26)
    add("INVOICE", W - 80, 90, 56, True, "r")
    add(f"Invoice No: {inv['invoice_number']}", 80, 280, 30, True)
    add(f"Date: {fmt_date(inv)}", 80, 325, 30)
    add(f"Bill To: {inv['customer_name']}", 80, 390, 30, True)
    add(CUST_ADDR, 80, 435, 26)
    y = 520
    add("Description", 100, y, 28, True)
    add("Qty", 680, y, 28, True, "r")
    add("Unit Price", 900, y, 28, True, "r")
    add("Amount", W - 100, y, 28, True, "r")
    y += 70
    for it in inv["items"]:
        add(it["description"], 100, y)
        add(str(it["quantity"]), 680, y, a="r")
        add(m(it["unit_price"], inv), 900, y, a="r")
        add(m(it["amount"], inv), W - 100, y, a="r")
        y += 60
    y += 30
    add("Subtotal:", 900, y, 32, a="r")
    add(m(inv["subtotal"], inv), W - 100, y, 32, a="r")
    y += 52
    if inv["tax"] is not None:
        add(f"VAT ({inv['tax_rate']}%):", 900, y, 32, a="r")
        add(m(inv["tax"], inv), W - 100, y, 32, a="r")
        y += 52
    add("Total:", 900, y, 32, True, "r")
    add(f"{m(inv['total'], inv)} {inv['currency']}", W - 100, y, 32, True, "r")
    return L


@lru_cache(maxsize=None)
def font(size, bold):
    p = f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf"
    try:
        return ImageFont.truetype(p, size)
    except OSError:
        return ImageFont.load_default(size)


def render_image(inv):
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    for t, x, y, s, b, a in layout(inv):
        d.text((x, y), t, font=font(s, b), fill="black", anchor="ra" if a == "r" else "la")
    return im


def degrade(im, level):
    angle, blur, noise, q, scale = {1: (0.8, 0.6, 8, 60, 0.8), 2: (2.0, 1.1, 18, 35, 0.65)}[level]
    rng = np.random.default_rng(level)
    im = im.rotate(float(rng.uniform(-angle, angle)), resample=Image.BICUBIC, fillcolor="white")
    im = im.resize((int(W * scale), int(H * scale)), Image.LANCZOS).filter(ImageFilter.GaussianBlur(blur))
    arr = np.asarray(im).astype(np.int16)
    arr = np.clip(arr + rng.normal(0, noise, arr.shape).astype(np.int16), 0, 255).astype(np.uint8)
    return Image.fromarray(arr), q


# ---------- লেখক ----------
def save_digital_pdf(inv, path):
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    k = 595 / W
    for t, x, y, s, b, a in layout(inv):
        fs, name = s * k, ("hebo" if b else "helv")
        w = pymupdf.get_text_length(t, fontname=name, fontsize=fs)
        page.insert_text((x * k - (w if a == "r" else 0), y * k + fs), t, fontname=name, fontsize=fs)
    doc.save(path)
    doc.close()


def save_scanned_pdf(inv, path):
    im, q = degrade(render_image(inv), 1)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=q)
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_image(page.rect, stream=buf.getvalue())
    doc.save(path)
    doc.close()


def sheet_rows(inv):
    rows = [["Supplier", inv["supplier_name"]], ["Invoice No", inv["invoice_number"]],
            ["Date", fmt_date(inv)], ["Bill To", inv["customer_name"]],
            ["Currency", inv["currency"]], [],
            ["Description", "Qty", "Unit Price", "Amount"]]
    rows += [[i["description"], i["quantity"], i["unit_price"], i["amount"]] for i in inv["items"]]
    rows += [[], ["Subtotal", None, None, inv["subtotal"]]]
    if inv["tax"] is not None:
        rows.append([f"VAT ({inv['tax_rate']}%)", None, None, inv["tax"]])
    rows.append(["Total", None, None, inv["total"]])
    return rows


def save_xlsx(inv, path, multisheet):
    wb = openpyxl.Workbook()
    ws = wb.active
    if not multisheet:
        ws.title = "Invoice"
        for r in sheet_rows(inv):
            ws.append(r)
    else:
        ws.title = "Summary"
        for r in [["Supplier", inv["supplier_name"]], ["Invoice No", inv["invoice_number"]],
                  ["Date", fmt_date(inv)], ["Bill To", inv["customer_name"]],
                  ["Currency", inv["currency"]], ["Subtotal", inv["subtotal"]]] + \
                 ([[f"VAT ({inv['tax_rate']}%)", inv["tax"]]] if inv["tax"] is not None else []) + \
                 [["Total", inv["total"]]]:
            ws.append(r)
        it = wb.create_sheet("Items")
        it.append(["Description", "Qty", "Unit Price", "Amount"])
        for i in inv["items"]:
            it.append([i["description"], i["quantity"], i["unit_price"], i["amount"]])
    wb.save(path)


def save_csv(inv, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(sheet_rows(inv))


# ---------- মূল কাজ ----------
def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    entries = []

    def entry(file, kind, inv=None, issues=(), expect="done", note=""):
        entries.append({"file": file, "kind": kind, "expect": expect,
                        "expect_issues": list(issues), "note": note,
                        "truth": truth(inv) if inv else None})

    # ১. digital PDF (পরিষ্কার)
    first = None
    for i in range(6):
        inv = build(i)
        first = first or inv
        save_digital_pdf(inv, OUT / f"digital_{i + 1:02d}.pdf")
        entry(f"digital_{i + 1:02d}.pdf", "digital_pdf", inv)

    # ২. duplicate: একই ফাইলের কপি, আর একই invoice-এর ছবি
    shutil.copy(OUT / "digital_01.pdf", OUT / "dup_copy_of_digital_01.pdf")
    entry("dup_copy_of_digital_01.pdf", "dup_file", first, ["duplicate_file"])
    render_image(first).save(OUT / "dup_image_of_digital_01.png")
    entry("dup_image_of_digital_01.png", "dup_invoice", first, ["duplicate_invoice"])

    # ৩. scanned PDF
    for n, i in enumerate(range(6, 10), 1):
        inv = build(i)
        save_scanned_pdf(inv, OUT / f"scanned_{n:02d}.pdf")
        entry(f"scanned_{n:02d}.pdf", "scanned_pdf", inv)

    # ৪. পরিষ্কার PNG
    for n, i in enumerate(range(10, 14), 1):
        inv = build(i)
        render_image(inv).save(OUT / f"image_clean_{n:02d}.png")
        entry(f"image_clean_{n:02d}.png", "image_clean", inv)

    # ৫. নষ্ট ছবি (মাঝারি আর খুব নষ্ট)
    for level, rng_, kind in ((1, range(14, 16), "image_noisy_1"), (2, range(16, 18), "image_noisy_2")):
        for n, i in enumerate(rng_, 1):
            inv = build(i)
            im, q = degrade(render_image(inv), level)
            im.save(OUT / f"{kind}_{n:02d}.jpg", quality=q)
            entry(f"{kind}_{n:02d}.jpg", kind, inv)

    # ৬. spreadsheet
    inv = build(18)
    save_xlsx(inv, OUT / "sheet_single_01.xlsx", False)
    entry("sheet_single_01.xlsx", "xlsx", inv)
    inv = build(19)
    save_xlsx(inv, OUT / "sheet_multi_02.xlsx", True)
    entry("sheet_multi_02.xlsx", "xlsx", inv, note="একাধিক sheet")
    for n, i in enumerate((20, 21), 1):
        inv = build(i)
        save_csv(inv, OUT / f"table_{n:02d}.csv")
        entry(f"table_{n:02d}.csv", "csv", inv)

    # ৭. USD ও দশমিক
    for n, i in enumerate((22, 23), 1):
        inv = build(i, "USD")
        save_digital_pdf(inv, OUT / f"usd_{n:02d}.pdf")
        entry(f"usd_{n:02d}.pdf", "digital_usd", inv)

    # ৮. tax নেই
    inv = build(24, with_tax=False)
    save_digital_pdf(inv, OUT / "notax_01.pdf")
    entry("notax_01.pdf", "digital_notax", inv, note="tax null হওয়া উচিত")

    # ৯. ইচ্ছাকৃত ভুল (ground truth = ছাপা মান; সিস্টেমকে ভুলটা ধরতে হবে)
    inv = build(25)
    inv["total"] = round(inv["total"] + 2000, 2)
    save_digital_pdf(inv, OUT / "wrong_total_01.pdf")
    entry("wrong_total_01.pdf", "digital_wrong_total", inv, ["total_mismatch"])

    inv = build(26)
    inv["items"][0]["amount"] = round(inv["items"][0]["amount"] + 500, 2)
    finish(inv, inv["tax_rate"])
    save_digital_pdf(inv, OUT / "line_mismatch_01.pdf")
    entry("line_mismatch_01.pdf", "digital_line_mismatch", inv, ["line_item_mismatch"])

    # ১০. ব্যর্থতার পরীক্ষা
    (OUT / "corrupt_01.pdf").write_bytes(b"%PDF-1.4\n" + random.Random(5).randbytes(600))
    entry("corrupt_01.pdf", "corrupt", None, expect="failed")
    Image.new("RGB", (W, H), "white").save(OUT / "blank_01.png")
    entry("blank_01.png", "blank", None, expect="failed_or_review",
          note="কিছু বানানো চলবে না, সব ফিল্ড null")

    (OUT / "labels.json").write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
    kinds = {}
    for e in entries:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    print(f"{len(entries)} files in {OUT}")
    for k, v in kinds.items():
        print(f"  {k:24} {v}")


if __name__ == "__main__":
    main()