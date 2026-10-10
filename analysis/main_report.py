"""Quick status report for downloaded main-run files (M5). Not the M6 analysis.

    python analysis/main_report.py results/main

Per model x level x family: accuracy (strict), format fails, api errors, median
output tokens, mean cost per call. Also checks record counts per run file.
"""

import glob
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

FAMILIES = ["deduce", "arith", "distract"]
LEVELS = ["none", "low", "medium", "high"]


def load(root):
    runs = []
    for f in sorted(glob.glob(str(Path(root) / "**" / "*.run.json"), recursive=True)):
        d = json.load(open(f, encoding="utf-8"))
        recs = [s["results"][0].get("dictResult") for s in d.get("subruns", []) if s.get("results")]
        runs.append({
            "file": f, "task": d["taskVersion"]["name"], "model": d["modelVersion"]["slug"],
            "state": d["state"], "score": (d.get("results") or [{}])[0].get("numericResult", {}).get("value"),
            "n_subruns": len(d.get("subruns", [])), "records": [r for r in recs if r],
        })
    return runs


def cost(r):
    return None if r["cost_nanodollars"] is None else float(r["cost_nanodollars"]) / 1e9


def main(root):
    runs = load(root)
    total = 0.0
    print("| model | level | family | n | acc | format_fail | api_error | median out tok | mean $/call |")
    print("|---|---|---|---|---|---|---|---|---|")
    checks = []
    for run in sorted(runs, key=lambda x: (x["model"], LEVELS.index(x["task"].split("-")[-1]))):
        recs = run["records"]
        run_cost = sum(cost(r) or 0 for r in recs)
        total += run_cost
        level = run["task"].split("-")[-1]
        keys = Counter((r["item_id"], int(r["repeat"])) for r in recs)
        checks.append(f"{run['model']} {run['task']}: state={run['state'].split('_')[-1]} "
                      f"subruns={run['n_subruns']} records={len(recs)} unique(item,repeat)={len(keys)} "
                      f"dupes={sum(v > 1 for v in keys.values())} levels={sorted({r['level'] for r in recs})} "
                      f"score={run['score']} cost=${run_cost:.4f}")
        for fam in FAMILIES:
            rs = [r for r in recs if r["family"] == fam]
            ok = [r for r in rs if r["outcome"] != "api_error"]
            toks = [float(r["output_tokens"]) for r in ok if r["output_tokens"] is not None]
            cs = [cost(r) for r in rs if cost(r) is not None]
            acc = sum(r["outcome"] == "correct" for r in ok) / len(ok) if ok else None
            print(f"| {run['model']} | {level} | {fam} | {len(rs)} | "
                  f"{'-' if acc is None else f'{acc:.2f}'} | "
                  f"{sum(r['outcome'] == 'format_fail' for r in rs)} | "
                  f"{sum(r['outcome'] == 'api_error' for r in rs)} | "
                  f"{'-' if not toks else f'{st.median(toks):.0f}'} | "
                  f"{'-' if not cs else f'{sum(cs) / len(cs):.5f}'} |")
        errs = Counter(r["error"] for r in recs if r.get("error"))
        for e, n in errs.items():
            checks.append(f"   ERROR x{n} ({run['model']} {run['task']}): {e}")
        other = Counter(r["outcome"] for r in recs if r["outcome"] not in ("correct", "wrong", "format_fail", "api_error"))
        if other:
            checks.append(f"   UNEXPECTED outcomes {dict(other)}")
    print()
    for c in checks:
        print(c)
    print(f"\nTOTAL cost in {root}: ${total:.4f}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/main")
