from app.db.database import get_session


def get_db():
    with get_session() as s:
        yield s