import re

from .schemas import PageResult

_NO_RE = re.compile(
    r"invoice\s*(?:no\b\.?|number|#)\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\-/_.#]*)",
    re.IGNORECASE,
)


def _find_number(text):
    """page-এর text থেকে invoice number খোঁজে, normalize করে ফেরত দেয়। না পেলে None।"""
    m = _NO_RE.search(text)
    if not m:
        return None
    return re.sub(r"[^a-z0-9]", "", m.group(1).lower()) or None


def split_invoices(pages: list[PageResult]) -> list[list[PageResult]]:
    """page-গুলো invoice অনুযায়ী ভাগ করে। invoice number বদলালে নতুন গ্রুপ শুরু হয়।"""
    groups = []
    current = []
    current_no = None

    for page in pages:
        no = _find_number(page.text)

        if no and current_no and no != current_no:
            groups.append(current)      # আগের invoice শেষ
            current = []                # নতুন invoice শুরু

        if no:
            current_no = no

        current.append(page)

    if current:
        groups.append(current)
    return groups