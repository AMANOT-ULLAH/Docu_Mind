import pandas as pd
from .schemas import PageResult

def extract_excel(path):
    pages, tables, warnings = [], [], []
    try:
        xl = pd.ExcelFile(path)   # নষ্ট ফাইল হলে এখানেই error
    except Exception as e:
        raise ValueError(f"Corrupted or unreadable Excel file: {e}")

    for i, sheet in enumerate(xl.sheet_names, start=1):
        try:
            df = pd.read_excel(xl, sheet_name=sheet, dtype=str)  # সব string, যাতে 001 বা তারিখ না ভাঙে
            df = df.dropna(how="all").dropna(axis=1, how="all").fillna("")
            if df.empty:
                warnings.append(f"sheet '{sheet}' is empty")
                continue
            tables.append({
                "sheet": sheet,
                "columns": [str(c) for c in df.columns],
                "rows": df.to_dict(orient="records"),
                "row_count": len(df),
            })
            pages.append(PageResult(page_number=i, method="table",
                                    text=df.to_csv(index=False)))
        except Exception as e:
            warnings.append(f"sheet '{sheet}' failed: {e}")
    return pages, tables, warnings