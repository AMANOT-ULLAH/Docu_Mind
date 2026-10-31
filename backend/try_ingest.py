from app.db.database import init_db, get_session
from app.services.ingest import ingest_file

FILES = ["inv_digital.pdf", "inv_scanned.pdf", "inv_photo.jpg", "inv_notax.pdf"]

init_db()
with get_session() as s:
    for name in FILES:
        d = ingest_file(s, "../evaluation/sample_data/" + name)
        print(f"{d.id:>3}  {d.file_name:16} {d.status:8} review={d.needs_review!s:5} "
              f"issues={len(d.issues)}  events={[e.event for e in d.events]}")