from pathlib import Path

HERE = Path(__file__).parent


def patch(path, old, new):
    s = path.read_text(encoding="utf-8")
    assert s.count(old) == 1, f"{path.name}: expected text not found exactly once: {old[:60]!r}"
    path.write_text(s.replace(old, new), encoding="utf-8")
    print("patched", path.name)


# ১. model: নতুন দুটো কলাম
patch(HERE / "app" / "db" / "models.py",
      "    error: Mapped[Optional[str]] = mapped_column(Text)\n",
      "    error: Mapped[Optional[str]] = mapped_column(Text)\n"
      "    pages_done: Mapped[Optional[int]] = mapped_column(Integer, default=0)\n"
      "    pages_total: Mapped[Optional[int]] = mapped_column(Integer)\n")

# ২. পুরোনো DB-তে কলাম যোগ করার migration
(HERE / "app" / "db" / "migrate.py").write_text('''from sqlalchemy import inspect, text

# টেবিল -> {কলাম: DDL}। create_all পুরোনো টেবিলে কলাম যোগ করে না, তাই এখানে যোগ করি।
NEW_COLUMNS = {
    "documents": {"pages_done": "INTEGER DEFAULT 0", "pages_total": "INTEGER"},
}


def ensure_columns(engine):
    """নেই এমন কলাম যোগ করে। যতবার ডাকো ফল একই (idempotent)। যোগ হওয়া কলামের তালিকা ফেরত দেয়।"""
    insp = inspect(engine)
    added = []
    with engine.begin() as conn:
        for table, cols in NEW_COLUMNS.items():
            if not insp.has_table(table):
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for name, ddl in cols.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
                    added.append(f"{table}.{name}")
    return added
''', encoding="utf-8")
print("created migrate.py")

# ৩. init_db-তে migration জোড়া
patch(HERE / "app" / "db" / "database.py",
      "    Base.metadata.create_all(get_engine())",
      "    Base.metadata.create_all(get_engine())\n"
      "    from app.db.migrate import ensure_columns\n"
      "    ensure_columns(get_engine())")

# ৪. crud: progress লেখার ফাংশন
crud = HERE / "app" / "db" / "crud.py"
t = crud.read_text(encoding="utf-8")
assert "def set_progress" not in t
crud.write_text(t.rstrip("\n") + '''


def set_progress(s, doc, done, total):
    doc.pages_done = done
    doc.pages_total = total
    s.commit()
''', encoding="utf-8")
print("patched crud.py")

# ৫. test
(HERE / "tests" / "test_migrate.py").write_text('''from sqlalchemy import create_engine, inspect, text

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
''', encoding="utf-8")
print("created test_migrate.py") 