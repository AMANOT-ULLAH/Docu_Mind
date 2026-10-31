import os
out = "../evaluation/sample_data/"
with open(out + "corrupted.pdf", "wb") as f:
    f.write(b"%PDF-1.4\n" + os.urandom(300))      # PDF-এর মতো শুরু, ভেতরে আবর্জনা
with open(out + "corrupted.png", "wb") as f:
    f.write(os.urandom(400))
with open(out + "notes.txt", "w") as f:
    f.write("this type is not supported")
print("done")