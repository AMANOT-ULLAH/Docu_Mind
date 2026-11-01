import pytest

from app.processors.csv_processor import extract_csv

RAGGED = ("Supplier,Dhaka Office Supplies Ltd\nInvoice No,INV-1\n\n"
          "Description,Qty,Unit Price,Amount\nChair,2,100,200\n"
          "Subtotal,,,200\nTotal,,,200\n")


def write(tmp_path, content, name="t.csv"):
    p = tmp_path / name
    p.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
    return p


def test_ragged_csv_is_read_as_raw_grid(tmp_path):
    pages, tables, warnings = extract_csv(write(tmp_path, RAGGED))
    text = pages[0].text
    assert "INV-1" in text
    assert "Chair,2,100,200" in text
    assert any("irregular" in w for w in warnings)
    assert tables[0]["row_count"] == 6          # ফাঁকা সারি বাদ


def test_ragged_semicolon_csv(tmp_path):
    p = write(tmp_path, "Supplier;X\nInvoice;Y\nDesc;Qty;Price\nChair;2;100\n")
    pages, _, warnings = extract_csv(p)
    assert "Chair,2,100" in pages[0].text
    assert any("irregular" in w for w in warnings)


def test_regular_csv_still_uses_table_path(tmp_path):
    pages, tables, warnings = extract_csv(write(tmp_path, "A,B\n1,2\n3,4\n"))
    assert tables[0]["columns"] == ["A", "B"]
    assert tables[0]["row_count"] == 2
    assert warnings == []


def test_regular_semicolon_csv(tmp_path):
    _, tables, _ = extract_csv(write(tmp_path, "A;B\n1;2\n"))
    assert tables[0]["columns"] == ["A", "B"]


def test_utf8_bom_is_stripped(tmp_path):
    _, tables, _ = extract_csv(write(tmp_path, "\ufeffA,B\n1,2\n"))
    assert tables[0]["columns"] == ["A", "B"]


def test_latin1_fallback_warns(tmp_path):
    p = write(tmp_path, "Name,Amount\nCaf\xe9,5\n".encode("latin-1"))
    pages, _, warnings = extract_csv(p)
    assert any("fallback" in w for w in warnings)
    assert "Café" in pages[0].text


def test_binary_garbage_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        extract_csv(write(tmp_path, b"\x00\x01\x02binary\x00junk"))


def test_empty_file_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        extract_csv(write(tmp_path, ""))

def test_ragged_csv_loses_no_cells(tmp_path):
    pages, _, _ = extract_csv(write(tmp_path, RAGGED))
    for cell in ["Supplier", "Dhaka Office Supplies Ltd", "Invoice No", "INV-1",
                 "Description", "Qty", "Unit Price", "Amount", "Chair", "2", "100", "200",
                 "Subtotal", "Total"]:
        assert cell in pages[0].text, f"lost cell: {cell}"