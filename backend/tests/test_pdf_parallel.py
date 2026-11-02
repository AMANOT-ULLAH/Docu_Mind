import threading
import time

import pymupdf
import pytest

from app.processors import pdf_processor as P


def make_blank_pdf(path, n):
    """n টা ফাঁকা পেজ (text নেই, তাই scanned ধরা হবে)। পেজ i-এর প্রস্থ 100+i।"""
    doc = pymupdf.open()
    for i in range(1, n + 1):
        doc.new_page(width=100 + i, height=150)
    doc.save(path)
    doc.close()


def page_no(img):
    return round(img.width * 72 / 200) - 100      # dpi=200 ধরে প্রস্থ থেকে পেজ নম্বর


@pytest.fixture
def fake_ocr(monkeypatch):
    calls = []

    def fake(img, lang):
        n = page_no(img)
        calls.append(n)
        time.sleep(max(0.01, 0.3 - 0.03 * n))      # প্রথম পেজ সবচেয়ে ধীর, তাই শেষ হওয়ার ক্রম উল্টো
        return f"text-{n}", 90.0, 0.0

    monkeypatch.setattr(P, "ocr_image", fake)
    return calls


def test_parallel_keeps_page_order(tmp_path, fake_ocr):
    p = tmp_path / "a.pdf"
    make_blank_pdf(p, 8)
    pages, warnings = P.extract_pdf_pages(p, workers=4)
    assert [x.page_number for x in pages] == list(range(1, 9))
    assert [x.text for x in pages] == [f"text-{i}" for i in range(1, 9)]
    assert warnings == []


def test_parallel_matches_sequential(tmp_path, fake_ocr):
    p = tmp_path / "a.pdf"
    make_blank_pdf(p, 6)
    seq, _ = P.extract_pdf_pages(p, workers=1)
    par, _ = P.extract_pdf_pages(p, workers=4)
    assert [x.model_dump() for x in seq] == [x.model_dump() for x in par]


def test_parallel_is_actually_faster(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "ocr_image", lambda img, lang: (time.sleep(0.2) or ("t", 90.0, 0.0)))
    p = tmp_path / "a.pdf"
    make_blank_pdf(p, 8)
    t = time.perf_counter()
    P.extract_pdf_pages(p, workers=1)
    seq = time.perf_counter() - t
    t = time.perf_counter()
    P.extract_pdf_pages(p, workers=4)
    par = time.perf_counter() - t
    assert par < seq * 0.7, f"sequential {seq:.2f}s vs parallel {par:.2f}s"


def test_one_failing_page_does_not_stop_others(tmp_path, monkeypatch):
    def fake(img, lang):
        if page_no(img) == 3:
            raise RuntimeError("ocr exploded")
        return "ok", 90.0, 0.0

    monkeypatch.setattr(P, "ocr_image", fake)
    p = tmp_path / "a.pdf"
    make_blank_pdf(p, 5)
    pages, warnings = P.extract_pdf_pages(p, workers=3)
    assert [x.page_number for x in pages] == [1, 2, 4, 5]
    assert len(warnings) == 1 and "page 3 failed" in warnings[0]


def test_progress_reaches_total(tmp_path, fake_ocr):
    p = tmp_path / "a.pdf"
    make_blank_pdf(p, 6)
    seen, lock = [], threading.Lock()

    def progress(done, total):
        with lock:
            seen.append((done, total))

    P.extract_pdf_pages(p, workers=3, progress=progress)
    assert len(seen) == 7
    assert seen[0] == (0, 6)          # শুরুতেই মোট পেজ জানানো হয়
    assert all(t == 6 for _, t in seen)
    assert sorted(d for d, _ in seen) == [0, 1, 2, 3, 4, 5, 6]


def test_broken_progress_callback_is_ignored(tmp_path, fake_ocr):
    p = tmp_path / "a.pdf"
    make_blank_pdf(p, 3)

    def bad(done, total):
        raise ValueError("boom")

    pages, _ = P.extract_pdf_pages(p, workers=2, progress=bad)
    assert len(pages) == 3


def test_digital_pages_do_not_use_ocr(tmp_path, fake_ocr):
    p = tmp_path / "d.pdf"
    doc = pymupdf.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text((50, 80), "This page has plenty of real digital text on it " + str(i))
    doc.save(p)
    doc.close()
    pages, _ = P.extract_pdf_pages(p, workers=4)
    assert [x.method for x in pages] == ["digital"] * 3
    assert fake_ocr == []