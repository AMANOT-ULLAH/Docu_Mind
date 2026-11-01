from app.db.database import init_db, get_session
from app.db import crud
from app.search import service

init_db()   # document_chunks table বানায়
with get_session() as s:
    for d in crud.list_documents(s, status="done", limit=200):
        d = crud.get_document(s, d.id)
        print(d.id, d.file_name, "chunks:", service.index_document(s, d))