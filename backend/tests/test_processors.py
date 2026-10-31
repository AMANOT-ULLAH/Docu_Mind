import os
import pymupdf
import pandas as pd

from app.processors.router import process_document

TEXT = "Invoice Number INV-1025 Total 11500"


# ---------- test ফাইল বানানোর helper ----------

def make_digital_pdf(path):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 100), TEXT, fontsize=24)
    doc.save(str(path))

def make_scanned_pdf(path):
    src = pymupdf.open()
    src.new_page().insert_text((72, 100), TEXT, fontsize=24)
    pix = src[0].get_pixmap(dpi=150)
    out = pymupdf.open()
    page = out.new_page(width=src[0].rect.width, height=src[0].rect.height)
    page.insert_image(page.rect, pixmap=pix)     # শুধু ছবি, কোনো text নেই
    out.save(str(path))

def make_png(path):
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 100), TEXT, fontsize=24)
    doc[0].get_pixmap(dpi=150).save(str(path))


# ---------- PDF ----------

def test_digital_pdf_uses_text_extraction(tmp_path):
    f = tmp_path / "digital.pdf"
    make_digital_pdf(f)
    r = process_document(f)
    assert r.status == "success"
    assert r.pages[0].method == "digital"
    assert "INV-1025" in r.pages[0].text

def test_scanned_pdf_falls_back_to_ocr(tmp_path):
    f = tmp_path / "scanned.pdf"
    make_scanned_pdf(f)
    r = process_document(f)
    assert r.status == "success"
    assert r.pages[0].method == "ocr"
    assert "1025" in r.pages[0].text
    assert r.pages[0].confidence > 50


# ---------- Image ----------

def test_png_ocr(tmp_path):
    f = tmp_path / "invoice.png"
    make_png(f)
    r = process_document(f)
    assert r.status == "success"
    assert "1025" in r.pages[0].text


# ---------- Excel / CSV ----------

def test_excel_reads_all_sheets(tmp_path):
    f = tmp_path / "multi.xlsx"
    with pd.ExcelWriter(f) as w:
        pd.DataFrame({"a": [1]}).to_excel(w, sheet_name="One", index=False)
        pd.DataFrame({"b": [2]}).to_excel(w, sheet_name="Two", index=False)
    r = process_document(f)
    assert r.status == "success"
    assert [t["sheet"] for t in r.tables] == ["One", "Two"]

def test_excel_keeps_leading_zeros(tmp_path):
    f = tmp_path / "ids.xlsx"
    pd.DataFrame({"invoice_no": ["00123"]}).to_excel(f, index=False)
    r = process_document(f)
    assert r.tables[0]["rows"][0]["invoice_no"] == "00123"

def test_csv_fallback_encoding(tmp_path):
    f = tmp_path / "euro.csv"
    f.write_bytes("item;price\nCoffee;3€\n".encode("cp1252"))
    r = process_document(f)
    assert r.status == "success"
    assert any("fallback encoding" in w for w in r.warnings)


# ---------- Failure scenarios: crash করা চলবে না ----------

def test_corrupted_pdf_fails_gracefully(tmp_path):
    f = tmp_path / "bad.pdf"
    f.write_bytes(b"%PDF-1.4\n" + os.urandom(300))
    r = process_document(f)
    assert r.status == "failed" and r.errors

def test_corrupted_image_fails_gracefully(tmp_path):
    f = tmp_path / "bad.png"
    f.write_bytes(os.urandom(400))
    r = process_document(f)
    assert r.status == "failed" and r.errors

def test_corrupted_excel_fails_gracefully(tmp_path):
    f = tmp_path / "bad.xlsx"
    f.write_bytes(os.urandom(500))
    r = process_document(f)
    assert r.status == "failed" and r.errors

def test_unsupported_type_rejected(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("hello")
    r = process_document(f)
    assert r.status == "failed"
    assert "Unsupported" in r.errors[0]

def test_empty_file_rejected(tmp_path):
    f = tmp_path / "empty.csv"
    f.write_text("")
    r = process_document(f)
    assert r.status == "failed"

def test_missing_file_does_not_crash(tmp_path):
    r = process_document(tmp_path / "nope.pdf")
    assert r.status == "failed"

def test_same_content_same_hash(tmp_path):
    a, b = tmp_path / "a.pdf", tmp_path / "b.pdf"
    make_digital_pdf(a)
    b.write_bytes(a.read_bytes())
    assert process_document(a).file_hash == process_document(b).file_hash