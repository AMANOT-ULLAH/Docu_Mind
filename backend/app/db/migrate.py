from sqlalchemy import inspect, text

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
