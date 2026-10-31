import pymupdf

src = pymupdf.open("../evaluation/sample_data/test.pdf")
out = pymupdf.open()

for page in src:
    pix = page.get_pixmap(dpi=150)                      # page-কে ছবি বানাও
    new_page = out.new_page(width=page.rect.width, height=page.rect.height)
    new_page.insert_image(new_page.rect, pixmap=pix)    # শুধু ছবি বসাও, text নেই

out.save("../evaluation/sample_data/scanned_test.pdf")
print("saved scanned_test.pdf")