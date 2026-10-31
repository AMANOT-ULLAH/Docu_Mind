from app.validation.duplicates import file_hash, invoice_key, find_duplicates


def f(value):
    return {"value": value, "evidence": "x", "confidence": "high"}


def ex(no="INV-1025", supplier="ABC Ltd", date="2026-10-15"):
    return {"invoice_number": f(no), "supplier_name": f(supplier), "invoice_date": f(date)}


def rec(id_, h=None, key=None):
    return {"id": id_, "file_hash": h, "key": key}


def kinds(issues):
    return [i["type"] for i in issues]


def test_same_file_hash_is_duplicate_file():
    r = find_duplicates("abc", None, [rec(1, h="abc")])
    assert kinds(r) == ["duplicate_file"]


def test_same_key_different_file_is_duplicate_invoice():
    k = invoice_key(ex())
    r = find_duplicates("new", k, [rec(1, h="old", key=k)])
    assert kinds(r) == ["duplicate_invoice"]


def test_ocr_noise_in_invoice_number_still_matches():
    clean = invoice_key(ex(no="INV-2026-1025"))
    noisy = invoice_key(ex(no="IN'V-2026- 1025"))
    assert clean == noisy


def test_case_and_spacing_ignored():
    assert invoice_key(ex(supplier="ABC Ltd")) == invoice_key(ex(supplier="abc  LTD"))


def test_different_invoice_number_not_duplicate():
    a, b = invoice_key(ex(no="INV-1")), invoice_key(ex(no="INV-2"))
    assert find_duplicates("n", b, [rec(1, h="o", key=a)]) == []


def test_different_supplier_not_duplicate():
    a, b = invoice_key(ex(supplier="ABC")), invoice_key(ex(supplier="XYZ"))
    assert find_duplicates("n", b, [rec(1, h="o", key=a)]) == []


def test_missing_field_gives_no_key_and_no_false_duplicate():
    assert invoice_key(ex(no=None)) is None
    assert find_duplicates("n", None, [rec(1, h="o", key=None)]) == []


def test_hash_and_key_both_match_reported_once():
    k = invoice_key(ex())
    r = find_duplicates("same", k, [rec(1, h="same", key=k)])
    assert kinds(r) == ["duplicate_file"]


def test_empty_known_list():
    assert find_duplicates("h", "k", []) == []


def test_file_hash_same_content_same_hash(tmp_path):
    a, b, c = tmp_path / "a.bin", tmp_path / "b.bin", tmp_path / "c.bin"
    a.write_bytes(b"hello")
    b.write_bytes(b"hello")
    c.write_bytes(b"hellO")
    assert file_hash(a) == file_hash(b)
    assert file_hash(a) != file_hash(c)