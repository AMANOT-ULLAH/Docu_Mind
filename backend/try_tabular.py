import sys
from app.processors.excel_processor import extract_excel
from app.processors.csv_processor import extract_csv

path = sys.argv[1]
fn = extract_excel if path.lower().endswith((".xlsx", ".xls")) else extract_csv
try:
    pages, tables, warns = fn(path)
    for t in tables:
        print(t["sheet"], "| rows:", t["row_count"], "| cols:", t["columns"])
    print("warnings:", warns)
except ValueError as e:
    print("FAILED (handled):", e)