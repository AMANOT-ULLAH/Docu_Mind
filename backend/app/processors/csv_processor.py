import csv
import io

import pandas as pd

from .schemas import PageResult

ENCODINGS = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
DELIMITERS = [",", ";", "\t", "|"]


def _decode(path):
    raw = open(path, "rb").read()
    if b"\x00" in raw:
        raise ValueError("Unreadable CSV: binary content (null bytes)")
    last_err = None
    for enc in ENCODINGS:
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError as e:
            last_err = e
    raise ValueError(f"Could not decode CSV: {last_err}")


def _guess_delimiter(text):
    lines = [ln for ln in text.splitlines() if ln.strip()][:20]
    counts = {d: sum(ln.count(d) for ln in lines) for d in DELIMITERS}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","


def _grid(text):
    """কাঁচা সারি-তালিকা (ফাঁকা সারি বাদ)। কলাম সংখ্যা সারিভেদে আলাদা হতে পারে।"""
    delim = _guess_delimiter(text)
    return [r for r in csv.reader(io.StringIO(text), delimiter=delim)
            if any(c.strip() for c in r)]


def _read_regular(text):
    """সব সারিতে সমান কলাম থাকলে pandas। না পারলে None।"""
    try:
        df = pd.read_csv(io.StringIO(text), dtype=str, sep=None, engine="python")
    except Exception:
        return None
    return df.dropna(how="all").fillna("")


def _read_irregular(text):
    """অসমান কলামের ফাইল (ওপরে supplier/তারিখ, নিচে item-এর টেবিল): কাঁচা grid হিসেবে পড়ে।"""
    rows = _grid(text)
    if not rows:
        raise ValueError("CSV has no data rows")
    width = max(len(r) for r in rows)
    cols = [f"col{i + 1}" for i in range(width)]
    records = [dict(zip(cols, r + [""] * (width - len(r)))) for r in rows]
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows(rows)
    return cols, records, out.getvalue()


def extract_csv(path):
    pages, tables, warnings = [], [], []
    text, used = _decode(path)
    if used not in ("utf-8-sig", "utf-8"):
        warnings.append(f"decoded with fallback encoding: {used}")

    # সব সারিতে সমান কলাম থাকলে তবেই pandas (নইলে সে চুপচাপ ডেটা কেটে ফেলে)
    uniform = len({len(r) for r in _grid(text)}) == 1
    df = _read_regular(text) if uniform else None
    if df is not None and not df.empty:
        tables.append({"sheet": "csv", "columns": [str(c) for c in df.columns],
                       "rows": df.to_dict(orient="records"), "row_count": len(df)})
        pages.append(PageResult(page_number=1, method="table", text=df.to_csv(index=False)))
        return pages, tables, warnings

    cols, records, body = _read_irregular(text)
    warnings.append("irregular CSV: rows have different column counts; read as raw grid")
    tables.append({"sheet": "csv", "columns": cols, "rows": records, "row_count": len(records)})
    pages.append(PageResult(page_number=1, method="table", text=body))
    return pages, tables, warnings
