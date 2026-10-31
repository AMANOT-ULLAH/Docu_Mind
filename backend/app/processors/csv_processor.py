import pandas as pd
from .schemas import PageResult

ENCODINGS = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]

def extract_csv(path):
    pages, tables, warnings = [], [], []
    df, used = None, None
    last_err = None
    for enc in ENCODINGS:
        try:
            # sep=None: comma, semicolon, tab নিজে চিনে নেয়
            df = pd.read_csv(path, encoding=enc, dtype=str, sep=None, engine="python")
            used = enc
            break
        except UnicodeDecodeError as e:
            last_err = e
        except Exception as e:
            raise ValueError(f"Unreadable CSV: {e}")
    if df is None:
        raise ValueError(f"Could not decode CSV: {last_err}")

    df = df.dropna(how="all").fillna("")
    if df.empty:
        raise ValueError("CSV has no data rows")
    if used != "utf-8-sig" and used != "utf-8":
        warnings.append(f"decoded with fallback encoding: {used}")

    tables.append({"sheet": "csv", "columns": [str(c) for c in df.columns],
                   "rows": df.to_dict(orient="records"), "row_count": len(df)})
    pages.append(PageResult(page_number=1, method="table", text=df.to_csv(index=False)))
    return pages, tables, warnings