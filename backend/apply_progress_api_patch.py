from pathlib import Path

HERE = Path(__file__).parent


def patch(path, old, new):
    s = path.read_text(encoding="utf-8")
    assert s.count(old) == 1, f"{path.name}: expected text not found exactly once: {old[:70]!r}"
    path.write_text(s.replace(old, new), encoding="utf-8")
    print("patched", path.name)


# ১. PDF খুলেই মোট পেজ জানাই
patch(HERE / "app" / "processors" / "pdf_processor.py",
      "    pool = ThreadPoolExecutor(max_workers=workers) if workers > 1 else None\n",
      "    if progress:\n"
      "        try:\n"
      "            progress(0, total)   # শুরুতেই মোট পেজ জানাই\n"
      "        except Exception:\n"
      "            pass\n\n"
      "    pool = ThreadPoolExecutor(max_workers=workers) if workers > 1 else None\n")

# ২. API: stage ও পেজ-progress
api = HERE / "app" / "api" / "documents.py"
patch(api, "def _summary(d):\n    ex = _effective(d) or {}\n",
      "def _stage(d):\n"
      '    """UI-র জন্য ধাপ: reading = পেজ পড়া চলছে, extracting = পেজ শেষ, AI কাজ করছে।"""\n'
      '    if d.status != "processing" or not d.pages_total:\n'
      "        return d.status\n"
      "    return \"extracting\" if (d.pages_done or 0) >= d.pages_total else \"reading\"\n\n\n"
      "def _summary(d):\n    ex = _effective(d) or {}\n")
patch(api, '"needs_review": d.needs_review, "created_at": d.created_at.isoformat(),',
      '"needs_review": d.needs_review, "created_at": d.created_at.isoformat(),\n'
      '            "stage": _stage(d), "pages_done": d.pages_done, "pages_total": d.pages_total,')

# ৩. আগের test: progress-এর প্রথম call এখন (0, total)
patch(HERE / "tests" / "test_pdf_parallel.py",
      "    assert len(seen) == 6\n"
      "    assert all(t == 6 for _, t in seen)\n"
      "    assert sorted(d for d, _ in seen) == [1, 2, 3, 4, 5, 6]\n",
      "    assert len(seen) == 7\n"
      "    assert seen[0] == (0, 6)          # শুরুতেই মোট পেজ জানানো হয়\n"
      "    assert all(t == 6 for _, t in seen)\n"
      "    assert sorted(d for d, _ in seen) == [0, 1, 2, 3, 4, 5, 6]\n")

# ৪. নতুন API test
tp = HERE / "tests" / "test_api.py"
t = tp.read_text(encoding="utf-8")
assert "test_detail_shows_page_progress" not in t
tp.write_text(t.rstrip("\n") + '''


def test_detail_shows_page_progress_and_stage(env):
    doc_id = upload(env, ("a.pdf", PDF, "application/pdf")).json()["documents"][0]["id"]
    d = crud.get_document(env.db, doc_id)
    crud.set_status(env.db, d, "processing")
    crud.set_progress(env.db, d, 40, 100)
    r = env.client.get(f"/documents/{doc_id}").json()
    assert (r["pages_done"], r["pages_total"], r["stage"]) == (40, 100, "reading")
    listed = env.client.get("/documents").json()["items"][0]
    assert (listed["pages_done"], listed["pages_total"]) == (40, 100)
    crud.set_progress(env.db, d, 100, 100)
    assert env.client.get(f"/documents/{doc_id}").json()["stage"] == "extracting"


def test_stage_is_plain_status_without_page_info(env):
    doc_id = upload(env, ("a.pdf", PDF, "application/pdf")).json()["documents"][0]["id"]
    assert env.client.get(f"/documents/{doc_id}").json()["stage"] == "queued"
''', encoding="utf-8")
print("patched test_api.py")