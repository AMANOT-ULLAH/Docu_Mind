import hashlib
from pathlib import Path

SUPPORTED = {
    ".pdf": "pdf",
    ".jpg": "image", ".jpeg": "image", ".png": "image",
    ".tif": "image", ".tiff": "image",
    ".xlsx": "excel", ".xls": "excel",
    ".csv": "csv",
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def detect_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext not in SUPPORTED:
        raise ValueError(f"Unsupported file type: {ext}")
    return SUPPORTED[ext]