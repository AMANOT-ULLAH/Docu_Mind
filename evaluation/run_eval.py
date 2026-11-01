"""Evaluation runner: dataset চালিয়ে আসল মাপ নেয়।
চালাও (evaluation/ ফোল্ডার থেকে): python run_eval.py [--sleep 4] [--limit N]"""
import argparse
import json
import re
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "backend"))
from app.services.pipeline import process_and_extract  # noqa: E402

DATA = HERE / "dataset"
RESULTS = HERE / "results"
FIELDS = ["invoice_number", "invoice_date", "supplier_name", "customer_name",
          "subtotal", "tax", "total", "currency"]
NUMERIC = {"subtotal", "tax", "total"}
TOL = 0.01


def norm(s):
    return None if s is None else re.sub(r"[^a-z0-9]", "", str(s).lower())


def field_ok(name, truth, pred):
    if truth is None or pred is None:
        return truth is None and pred is None
    if name in NUMERIC:
        try:
            return abs(float(truth) - float(pred)) <= TOL
        except (TypeError, ValueError):
            return False
    return norm(truth) == norm(pred)


def item_match(t, p):
    try:
        nums = all(p.get(k) is not None and abs(float(t[k]) - float(p[k])) <= TOL
                   for k in ("quantity", "unit_price", "amount"))
    except (TypeError, ValueError):
        return False
    a, b = norm(t["description"]), norm(p.get("description"))
    return nums and bool(a) and bool(b) and (a in b or b in a)


def items_hits(truth_items, pred_items):
    used, hit = set(), 0
    for t in truth_items:
        for j, p in enumerate(pred_items):
            if j not in used and item_match(t, p):
                used.add(j)
                hit += 1
                break
    return hit


def run_one(entry, known):
    rec = {"file": entry["file"], "kind": entry["kind"], "expect": entry["expect"]}
    t0 = time.perf_counter()
    try:
        out = process_and_extract(str(DATA / entry["file"]), known=known)
    except Exception as e:  # crash = সবচেয়ে খারাপ ফল
        rec.update(crashed=True, produced=False, seconds=round(time.perf_counter() - t0, 2),
                   error=f"{type(e).__name__}: {e}"[:300], fields={}, issues=[], flagged=False)
        return rec, None
    ex = out["extraction"]
    rec.update(
        crashed=False, produced=ex is not None, seconds=out["seconds"],
        file_seconds=out["file_seconds"], llm_seconds=out["llm_seconds"],
        provider=out["provider"], flagged=bool(out["review_reasons"]),
        review_reasons=out["review_reasons"], errors=out["errors"],
        issues=[i["type"] for i in (out["validation"] or {}).get("issues", [])])

    truth = entry["truth"]
    if truth is not None:
        pred = {f: (ex[f]["value"] if ex else None) for f in FIELDS}
        rec["pred"] = pred
        rec["fields"] = {f: bool(ex) and field_ok(f, truth[f], pred[f]) for f in FIELDS}
        rec["invented"] = [f for f in FIELDS if truth[f] is None and pred[f] is not None]
        pitems = ex["line_items"] if ex else []
        rec["items"] = [items_hits(truth["line_items"], pitems),
                        len(truth["line_items"]), len(pitems)]
    elif ex:  # ফাঁকা ফাইল: কোনো মান থাকলে সেটা বানানো
        rec["invented"] = [f for f in FIELDS if ex[f]["value"] is not None]

    if entry["expect"] == "done":
        rec["outcome_ok"] = rec["produced"]
    elif entry["expect"] == "failed":
        rec["outcome_ok"] = not rec["produced"]
    else:  # failed_or_review
        rec["outcome_ok"] = (not rec["produced"]) or not rec.get("invented")

    known_entry = {"id": entry["file"], "file_hash": out["file_hash"], "key": out["invoice_key"]}
    return rec, (known_entry if ex else None)


def pct(a, b):
    return round(100 * a / b, 1) if b else None


def summarize(recs):
    S = {"files": len(recs)}
    valid = [r for r in recs if r["expect"] == "done"]
    ok = [r for r in valid if r["produced"]]
    S["valid_documents"] = len(valid)
    S["extracted"] = len(ok)
    S["extraction_success_rate_%"] = pct(len(ok), len(valid))
    S["failure_rate_%"] = pct(len(valid) - len(ok), len(valid))
    S["crashes"] = sum(r["crashed"] for r in recs)
    bad = [r for r in recs if r["expect"] != "done"]
    S["bad_files_handled_correctly"] = f"{sum(r['outcome_ok'] for r in bad)}/{len(bad)}"
    S["all_outcomes_as_expected_%"] = pct(sum(r["outcome_ok"] for r in recs), len(recs))

    scored = [r for r in recs if "fields" in r]
    tot = sum(len(FIELDS) for _ in scored)
    good = sum(sum(r["fields"].values()) for r in scored)
    S["field_accuracy_%"] = pct(good, tot)
    S["field_accuracy_note"] = "extraction ব্যর্থ হলে ওই ফাইলের সব ফিল্ড ভুল ধরা হয়েছে"
    S["per_field_%"] = {f: pct(sum(r["fields"][f] for r in scored), len(scored)) for f in FIELDS}
    S["fully_correct_documents"] = (
        f"{sum(all(r['fields'].values()) and r['items'][0] == r['items'][1] for r in scored)}"
        f"/{len(scored)}")
    ih, it = sum(r["items"][0] for r in scored), sum(r["items"][1] for r in scored)
    S["line_item_accuracy_%"] = pct(ih, it)
    S["line_items_matched"] = f"{ih}/{it}"
    S["extra_line_items_invented"] = sum(max(0, r["items"][2] - r["items"][1]) for r in scored)
    S["invented_values"] = {r["file"]: r["invented"] for r in recs if r.get("invented")}

    kinds = defaultdict(lambda: [0, 0])
    for r in scored:
        kinds[r["kind"]][0] += sum(r["fields"].values())
        kinds[r["kind"]][1] += len(FIELDS)
    S["accuracy_by_kind_%"] = {k: pct(a, b) for k, (a, b) in kinds.items()}

    exp = [r for r in recs if r["file"] and r.get("produced") is not None and
           r["kind"] in {"dup_file", "dup_invoice", "digital_wrong_total", "digital_line_mismatch"}]
    S["validator_detected"] = {r["file"]: r["issues"] for r in exp}
    clean = [r for r in recs if r["expect"] == "done" and r["produced"] and r["kind"] not in
             {"dup_file", "dup_invoice", "digital_wrong_total", "digital_line_mismatch"}]
    fp = [r for r in clean if r["flagged"]]
    S["false_alarms"] = f"{len(fp)}/{len(clean)} ({pct(len(fp), len(clean))}%)"
    S["false_alarm_files"] = {r["file"]: r["review_reasons"] for r in fp}

    secs = sorted(r["seconds"] for r in recs if r.get("seconds") is not None)
    if secs:
        S["seconds"] = {"mean": round(statistics.mean(secs), 2), "median": round(statistics.median(secs), 2),
                        "p95": secs[int(0.95 * (len(secs) - 1))], "max": secs[-1], "total": round(sum(secs), 1)}
    llm = [r["llm_seconds"] for r in recs if r.get("llm_seconds") is not None]
    fil = [r["file_seconds"] for r in recs if r.get("file_seconds") is not None]
    S["mean_llm_seconds"] = round(statistics.mean(llm), 2) if llm else None
    S["mean_file_seconds"] = round(statistics.mean(fil), 2) if fil else None
    return S


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sleep", type=float, default=4.0, help="LLM call-এর পর বিরতি (free quota)")
    ap.add_argument("--limit", type=int, default=0, help="শুধু প্রথম N ফাইল (পরীক্ষার জন্য)")
    args = ap.parse_args()

    entries = json.loads((DATA / "labels.json").read_text(encoding="utf-8"))
    if args.limit:
        entries = entries[:args.limit]
    known, recs = [], []
    for n, e in enumerate(entries, 1):
        rec, kn = run_one(e, known)
        if kn:
            known.append(kn)
        recs.append(rec)
        wrong = [f for f, v in rec.get("fields", {}).items() if not v]
        print(f"[{n:>2}/{len(entries)}] {e['file']:30} {'OK ' if rec['outcome_ok' if 'outcome_ok' in rec else 'produced'] else 'BAD'}"
              f" {rec.get('seconds')}s  wrong={wrong or '-'}  issues={rec['issues'] or '-'}"
              + (f"  CRASH {rec['error']}" if rec['crashed'] else ""), flush=True)
        if rec.get("llm_seconds") is not None and n < len(entries):
            time.sleep(args.sleep)

    S = summarize(recs)
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "results.json").write_text(json.dumps(
        {"run_at": datetime.now().isoformat(timespec="seconds"), "summary": S, "records": recs},
        indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n===== SUMMARY =====")
    print(json.dumps(S, indent=2, ensure_ascii=False))
    print(f"\nসব বিস্তারিত: {RESULTS / 'results.json'}")


if __name__ == "__main__":
    main()