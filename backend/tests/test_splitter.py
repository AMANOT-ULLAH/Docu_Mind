from app.processors.schemas import PageResult
from app.processors.splitter import split_invoices


def P(n, text):
    return PageResult(page_number=n, method="digital", text=text)


def nums(groups):
    return [[p.page_number for p in g] for g in groups]


def test_one_invoice_per_page():
    pages = [P(1, "Invoice No: A-1\nTotal: 10"), P(2, "Invoice No: A-2\nTotal: 20")]
    assert nums(split_invoices(pages)) == [[1], [2]]


def test_multi_page_single_invoice():
    pages = [P(1, "Invoice No: A-1\nItem 1"), P(2, "Item 2"), P(3, "Total: 99")]
    assert nums(split_invoices(pages)) == [[1, 2, 3]]


def test_repeated_header_same_number_not_split():
    pages = [P(1, "Invoice No: A-1\nItem 1"), P(2, "Invoice No: A-1 (continued)\nItem 2")]
    assert nums(split_invoices(pages)) == [[1, 2]]


def test_no_invoice_number_means_single_group():
    pages = [P(1, "hello"), P(2, "world")]
    assert nums(split_invoices(pages)) == [[1, 2]]


def test_cover_page_joins_first_invoice():
    pages = [P(1, "cover"), P(2, "Invoice No: A-1"), P(3, "Invoice No: A-2")]
    assert nums(split_invoices(pages)) == [[1, 2], [3]]


def test_empty_input():
    assert split_invoices([]) == []


def test_invoice_date_is_not_an_invoice_number():
    pages = [P(1, "Invoice Date: 2026-10-15"), P(2, "Invoice Date: 2026-10-16")]
    assert nums(split_invoices(pages)) == [[1, 2]]