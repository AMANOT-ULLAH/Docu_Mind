from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app import config


class Base(DeclarativeBase):
    pass


_engine = None
_Session = None


def get_engine():
    """প্রথমবার ডাকলে engine বানায়। DATABASE_URL না থাকলে স্পষ্ট error দেয়।"""
    global _engine, _Session
    if _engine is None:
        if not config.DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not set in backend/.env")
        _engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
        _Session = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


@contextmanager
def get_session():
    get_engine()
    session = _Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """সব table বানায় (আগে থাকলে ছোঁয় না)।"""
    from app.db import models  # noqa: F401  (table-গুলো register করার জন্য)
    Base.metadata.create_all(get_engine())
    from app.db.migrate import ensure_columns
    ensure_columns(get_engine())