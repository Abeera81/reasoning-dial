"""Summarize downloaded dial-calibration run files (Tech Design §8, M3).

    python analysis/calibration_report.py results/calibration

Reads per-call records from subruns[].results[0].dictResult.
"""

import glob
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

FAMILIES = ["deduce", "arith", "distract"]
LEVELS = ["none", "high"]


def load(root):
    out = {}
    for f in sorted(glob.glob(str(Path(root) / "**" / "*.run.json"), recursive=True)):
        d = json.load(open(f, encoding="utf-8"))
        model = d["modelVersion"]["slug"]
        recs = [s["results"][0].get("dictResult") for s in d.get("subruns", []) if s.get("results")]
        out[model] = {"file": f, "state": d["state"], "records": [r for r in recs if r],
                      "n_subruns": len(d.get("subruns", [])), "error": d.get("errorMessage")}
    return out


def num(x):
    return None if x is None else float(x)


def summarize(records):
    main = [r for r in records if int(r.get("probe", 0)) == 0]
    rows = []
    for fam in FAMILIES:
        for lv in LEVELS:
            rs = [r for r in main if r["family"] == fam and r["level"] == lv]
            ok = [r for r in rs if r["outcome"] != "api_error"]
            toks = [num(r["output_tokens"]) for r in ok if r["output_tokens"] is not None]
            costs = [num(r["cost_nanodollars"]) / 1e9 for r in rs if r["cost_nanodollars"] is not None]
            lat = [num(r["latency_s"]) for r in rs if r["latency_s"] is not None]
            rows.append({
                "family": fam, "level": lv, "n": len(rs),
                "acc": sum(r["outcome"] == "correct" for r in ok) / len(ok) if ok else None,
                "format_fail": sum(r["outcome"] == "format_fail" for r in rs),
                "api_error": sum(r["outcome"] == "api_error" for r in rs),
                "med_tokens": st.median(toks) if toks else None,
                "mean_cost": sum(costs) / len(costs) if costs else None,
                "mean_latency": sum(lat) / len(lat) if lat else None,
                "errors": sorted({r["error"] for r in rs if r.get("error")}),
            })
    return rows


def fmt(x, spec):
    return "-" if x is None else format(x, spec)


def main(root):
    data = load(root)
    total = 0.0
    level_cost = defaultdict(dict)
    for model, d in data.items():
        recs = d["records"]
        cost = sum(num(r["cost_nanodollars"]) or 0 for r in recs) / 1e9
        total += cost
        print(f"\n## {model}  state={d['state']}  subruns={d['n_subruns']}  records={len(recs)}  "
              f"cost=${cost:.4f}  caching={sorted({str(r.get('caching')) for r in recs})}")
        if d["error"]:
            print(f"   run error: {d['error']}")
        print("| family | level | n | acc | format_fail | api_error | median out tok | mean cost | mean latency s |")
        print("|---|---|---|---|---|---|---|---|---|")
        for row in summarize(recs):
            print(f"| {row['family']} | {row['level']} | {row['n']} | {fmt(row['acc'], '.2f')} | "
                  f"{row['format_fail']} | {row['api_error']} | {fmt(row['med_tokens'], '.0f')} | "
                  f"{fmt(row['mean_cost'], '.5f')} | {fmt(row['mean_latency'], '.1f')} |")
            for e in row["errors"]:
                print(f"   ERROR ({row['family']}/{row['level']}): {e}")
        main_recs = [r for r in recs if int(r.get("probe", 0)) == 0]
        for lv in LEVELS:
            cs = [num(r["cost_nanodollars"]) / 1e9 for r in main_recs
                  if r["level"] == lv and r["cost_nanodollars"] is not None]
            level_cost[model][lv] = sum(cs) / len(cs) if cs else None
        # cache probe
        for iid in sorted({r["item_id"] for r in recs if int(r.get("probe", 0)) > 0}):
            pr = sorted((r for r in recs if r["item_id"] == iid and int(r["probe"]) > 0),
                        key=lambda r: int(r["probe"]))
            base = [r for r in main_recs if r["item_id"] == iid and r["level"] == "none"]
            texts = [r.get("raw") for r in pr]
            print(f"   cache probe {iid}: probe1==probe2 {len(texts) == 2 and texts[0] == texts[1]}; "
                  f"probe1==main {bool(base) and base[0].get('raw') == texts[0]}; "
                  f"lens main/p1/p2 {[len(x.get('raw') or '') for x in base + pr]}")
        # possible truncation: no FINAL ANSWER marker and long output
        trunc = [r for r in main_recs if r["outcome"] == "format_fail"]
        for r in trunc:
            tail = (r.get("raw") or "")[-120:].replace("\n", " | ")
            print(f"   format_fail {r['item_id']}/{r['level']}: out_tok={r['output_tokens']} tail=...{tail!r}")

    print(f"\nTOTAL cost across downloaded runs: ${total:.4f}")

    # difficulty check: median none-level accuracy across models
    print("\n## Difficulty (none level, median across models)")
    for fam in ["deduce", "arith", "distract"]:
        accs = []
        for model, d in data.items():
            row = next(x for x in summarize(d["records"]) if x["family"] == fam and x["level"] == "none")
            if row["acc"] is not None:
                accs.append(row["acc"])
        med = st.median(accs) if accs else None
        print(f"{fam}: per-model {[round(a, 2) for a in accs]} median={fmt(med, '.2f')}")

    # budget projection: cost ~ items x R x (c_none + c_high + 2 x (c_none + c_high)/2)
    print("\n## Main-run projection (4 levels; medium/low ~ mean of none and high)")
    print("| model | c_none | c_high | 60xR3 | 60xR2 | 45xR3 | 45xR2 |")
    print("|---|---|---|---|---|---|---|")
    tot = defaultdict(float)
    for model, c in level_cost.items():
        if c.get("none") is None or c.get("high") is None:
            print(f"| {model} | {c.get('none')} | {c.get('high')} | - | - | - | - |")
            continue
        per = 2 * (c["none"] + c["high"])
        vals = {(n, r): n * r * per for n in (60, 45) for r in (3, 2)}
        for k, v in vals.items():
            tot[k] += v
        print(f"| {model} | {c['none']:.5f} | {c['high']:.5f} | ${vals[(60, 3)]:.2f} | "
              f"${vals[(60, 2)]:.2f} | ${vals[(45, 3)]:.2f} | ${vals[(45, 2)]:.2f} |")
    print(f"| **total** | | | ${tot[(60, 3)]:.2f} | ${tot[(60, 2)]:.2f} | ${tot[(45, 3)]:.2f} | ${tot[(45, 2)]:.2f} |")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/calibration")
