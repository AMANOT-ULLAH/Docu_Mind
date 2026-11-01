from pathlib import Path

HERE = Path(__file__).parent


def patch(fname, old, new):
    p = HERE / fname
    s = p.read_text(encoding="utf-8")
    assert s.count(old) == 1, f"{fname}: expected text not found exactly once"
    p.write_text(s.replace(old, new), encoding="utf-8")
    print("patched", fname)


# ---- run_eval.py: মিছে alarm-এর সঠিক সংজ্ঞা + নিঃশব্দ ভুল ----
patch("run_eval.py",
'''    clean = [r for r in recs if r["expect"] == "done" and r["produced"] and r["kind"] not in
             {"dup_file", "dup_invoice", "digital_wrong_total", "digital_line_mismatch"}]
    fp = [r for r in clean if r["flagged"]]
    S["false_alarms"] = f"{len(fp)}/{len(clean)} ({pct(len(fp), len(clean))}%)"
    S["false_alarm_files"] = {r["file"]: r["review_reasons"] for r in fp}
''',
'''    planted = {"dup_file", "dup_invoice", "digital_wrong_total", "digital_line_mismatch"}

    def right(r):
        return "fields" in r and all(r["fields"].values()) and r["items"][0] == r["items"][1]

    wrong_docs = [r for r in scored if r["produced"] and not right(r)]
    caught = [r for r in wrong_docs if r["flagged"]]
    silent = [r for r in wrong_docs if not r["flagged"]]
    S["documents_with_wrong_values"] = len(wrong_docs)
    S["wrong_and_flagged_for_review"] = len(caught)
    S["silent_errors_wrong_but_not_flagged"] = {
        r["file"]: [f for f, v in r["fields"].items() if not v] or ["line_items"] for r in silent}
    S["silent_error_count"] = len(silent)

    clean = [r for r in scored if r["produced"] and r["kind"] not in planted and right(r)]
    fp = [r for r in clean if r["flagged"]]
    S["false_alarms_on_correct_docs"] = f"{len(fp)}/{len(clean)} ({pct(len(fp), len(clean))}%)"
    S["false_alarm_files"] = {r["file"]: r["review_reasons"] for r in fp}
''')

# ---- make_dataset.py: আরও কঠিন নষ্ট ছবি (স্তর ৩) ----
patch("make_dataset.py",
"2: (2.0, 1.1, 18, 35, 0.65)}[level]",
"2: (2.0, 1.1, 18, 35, 0.65),\n                                  3: (4.0, 1.8, 30, 22, 0.5)}[level]")

patch("make_dataset.py",
'(2, range(16, 18), "image_noisy_2")):',
'(2, range(16, 18), "image_noisy_2"),\n                                (3, range(27, 30), "image_noisy_3")):')