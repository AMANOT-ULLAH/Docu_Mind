import pandas as pd, os
out = "../evaluation/sample_data/"

inv = pd.DataFrame({"item": ["Product A", "Product B"], "qty": [2, 3], "price": [1000, 1500]})
tax = pd.DataFrame({"subtotal": [6500], "tax": [650], "total": [7150]})
with pd.ExcelWriter(out + "invoice_multi.xlsx") as w:        # ২ sheet-এর Excel
    inv.to_excel(w, sheet_name="Items", index=False)
    tax.to_excel(w, sheet_name="Totals", index=False)

inv.to_csv(out + "invoice.csv", index=False)                  # সাধারণ CSV
with open(out + "invoice_cp1252.csv", "wb") as f:             # ভিন্ন encoding (€ চিহ্ন)
    f.write("item;price\nCoffee;3€\n".encode("cp1252"))

with open(out + "corrupted.xlsx", "wb") as f:                 # নষ্ট ফাইল
    f.write(os.urandom(500))
open(out + "empty.csv", "w").close()                          # খালি ফাইল
print("done")