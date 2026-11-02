from sqlalchemy import create_engine, inspect, text

from app.db.migrate import ensure_columns


def old_db(tmp_path):
    """নতুন কলাম আসার আগের অবস্থার DB, একটা সারি সহ।"""
    e = create_engine(f"sqlite:///{tmp_path / 't.db'}")
    with e.begin() as c:
        c.execute(text("CREATE TABLE documents (id INTEGER PRIMARY KEY, file_name TEXT)"))
        c.execute(text("INSERT INTO documents (id, file_name) VALUES (1, 'a.pdf')"))
    return e


def cols(e):
    return {c["name"] for c in inspect(e).get_columns("documents")}


def test_adds_missing_columns(tmp_path):
    e = old_db(tmp_path)
    added = ensure_columns(e)
    assert sorted(added) == ["documents.pages_done", "documents.pages_total"]
    assert {"pages_done", "pages_total"} <= cols(e)


def test_is_idempotent(tmp_path):
    e = old_db(tmp_path)
    ensure_columns(e)
    assert ensure_columns(e) == []


def test_existing_rows_survive_with_default(tmp_path):
    e = old_db(tmp_path)
    ensure_columns(e)
    with e.connect() as c:
        row = c.execute(text("SELECT file_name, pages_done, pages_total FROM documents")).one()
    assert row == ("a.pdf", 0, None)


def test_missing_table_is_skipped(tmp_path):
    e = create_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    assert ensure_columns(e) == []
