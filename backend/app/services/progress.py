import threading
import time

from sqlalchemy import update

from app.db.database import get_session
from app.db.models import Document


class ProgressWriter:
    """progress(done, total) ডাকলে সর্বোচ্চ প্রতি min_interval সেকেন্ডে DB-তে লেখে।
    শেষ পেজ (done == total) সবসময় লেখা হয়। যেকোনো thread থেকে ডাকা যায়, আর
    লেখা ব্যর্থ হলে প্রসেসিং নষ্ট করে না।"""

    def __init__(self, doc_id, min_interval=2.0):
        self.doc_id = doc_id
        self.min_interval = min_interval
        self._last = 0.0
        self._lock = threading.Lock()

    def __call__(self, done, total):
        now = time.monotonic()
        with self._lock:
            if done < total and now - self._last < self.min_interval:
                return
            self._last = now
        try:
            with get_session() as s:
                s.execute(update(Document).where(Document.id == self.doc_id)
                          .values(pages_done=done, pages_total=total))
        except Exception:
            pass
