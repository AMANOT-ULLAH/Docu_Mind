from app.validation.invoice_validator import validate_invoice


def field(value, evidence=None, confidence="high"):
    return {"value": value, "evidence": evidence, "confidence": confidence}


def make(**over):
    """সম্পূর্ণ ঠিক একটা invoice। যে field বদলাতে চাও শুধু সেটা দাও।"""
    base = {
        "invoice_number": field("INV-1025", "Invoice No: INV-1025"),
        "invoice_date": field("2026-10-15", "Date: 15 Oct 2026"),
        "supplier_name": field("ABC Ltd", "ABC Ltd"),
        "customer_name": field("XYZ Corp", "Bill To: XYZ Corp"),
        "subtotal": field(10000, "Subtotal: 10,000"),
        "tax": field(1500, "Tax: 1,500"),
        "total": field(11500, "Total: 11,500"),
        "currency": field("BDT", "BDT"),
        "line_items": [
            {"description": "A", "quantity": 2, "unit_price": 3000,
             "amount": 6000, "evidence": "A 2 3000 6000"},
            {"description": "B", "quantity": 4, "unit_price": 1000,
             "amount": 4000, "evidence": "B 4 1000 4000"},
        ],
        "notes": [],
    }
    base.update(over)
    return base


def kinds(report):
    return [i["type"] for i in report["issues"]]


def test_clean_invoice_is_ok():
    r = validate_invoice(make())
    assert r["status"] == "ok"
    assert r["issues"] == []


def test_total_mismatch_assignment_example():
    # assignment-এর উদাহরণ: 10000 + 1500 হওয়া উচিত 11500, লেখা আছে 15000
    r = validate_invoice(make(total=field(15000, "Total: 15,000")))
    issue = next(i for i in r["issues"] if i["type"] == "total_mismatch")
    assert issue["expected"] == "11500"
    assert issue["actual"] == "15000"
    assert r["status"] == "review_required"


def test_small_rounding_difference_is_tolerated():
    r = validate_invoice(make(total=field(11500.005, "Total: 11,500.005")))
    assert "total_mismatch" not in kinds(r)


def test_float_trap_uses_decimal():
    # float-এ 0.1 + 0.2 != 0.3; Decimal-এ ঠিক মেলে
    r = validate_invoice(make(subtotal=field(0.1, "Subtotal: 0.1"),
                              tax=field(0.2, "Tax: 0.2"),
                              total=field(0.3, "Total: 0.3"),
                              line_items=[]))
    assert "total_mismatch" not in kinds(r)


def test_missing_required_field():
    r = validate_invoice(make(invoice_number=field(None, None, "low")))
    assert "missing_field" in kinds(r)
    assert r["status"] == "review_required"


def test_tax_missing_and_total_equals_subtotal_is_ok():
    r = validate_invoice(make(tax=field(None, None, "low"),
                              total=field(10000, "Total: 10,000")))
    assert r["status"] == "ok"


def test_tax_missing_but_total_differs():
    r = validate_invoice(make(tax=field(None, None, "low")))   # total 11500, subtotal 10000
    assert "total_mismatch" in kinds(r)


def test_line_item_arithmetic_mismatch():
    bad = [{"description": "A", "quantity": 2, "unit_price": 3000,
            "amount": 5000, "evidence": "x"}]
    r = validate_invoice(make(line_items=bad))
    assert "line_item_mismatch" in kinds(r)


def test_line_items_do_not_add_up_to_subtotal():
    items = [  # প্রতিটা line নিজে ঠিক, কিন্তু যোগফল 9000 (subtotal 10000)
        {"description": "A", "quantity": 2, "unit_price": 3000, "amount": 6000, "evidence": "x"},
        {"description": "B", "quantity": 3, "unit_price": 1000, "amount": 3000, "evidence": "x"},
    ]
    r = validate_invoice(make(line_items=items))
    assert "subtotal_mismatch" in kinds(r)
    assert "line_item_mismatch" not in kinds(r)


def test_negative_value_flagged():
    r = validate_invoice(make(tax=field(-1500, "Tax: -1,500")))
    assert "negative_value" in kinds(r)


def test_suspicious_invoice_number():
    r = validate_invoice(make(invoice_number=field("IN'V-2026- 1025", "x")))
    assert "suspicious_format" in kinds(r)


def test_unknown_currency():
    r = validate_invoice(make(currency=field("BOT", "BOT")))
    assert "unknown_currency" in kinds(r)


def test_ambiguous_decimal_is_warning():
    r = validate_invoice(make(subtotal=field(7.05, "Subtotal: 7.050")))
    issue = next(i for i in r["issues"] if i["type"] == "ambiguous_number")
    assert issue["severity"] == "warning"


def test_model_note_triggers_review():
    r = validate_invoice(make(notes=["date looks unclear"]))
    assert "model_note" in kinds(r)
    assert r["status"] == "review_required"


def test_low_confidence_value_flagged():
    r = validate_invoice(make(invoice_number=field("INV-1025", "x", "low")))
    assert "low_confidence" in kinds(r)