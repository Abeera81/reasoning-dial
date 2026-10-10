"""Synthetic-data checks for analysis/analyze.py: bootstrap, Holm, ceiling, pipeline."""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
import analyze as A  # noqa: E402


# ---------------------------------------------------------------- bootstrap

def test_bootstrap_acc_point_and_ci():
    c = np.array([2, 2, 1, 0] * 5)          # 20 items, 2 calls each -> 25/40
    n = np.full(20, 2)
    acc, lo, hi = A.bootstrap_acc(c, n, reps=2000)
    assert acc == pytest.approx(25 / 40)
    assert lo < acc < hi
    assert 0.3 < lo and hi < 0.9


def test_bootstrap_deterministic_and_degenerate():
    c, n = np.array([1, 0, 2, 1]), np.array([2, 2, 2, 2])
    assert A.bootstrap_acc(c, n, reps=500) == A.bootstrap_acc(c, n, reps=500)
    assert A.bootstrap_acc(np.full(10, 2), np.full(10, 2), reps=500) == (1.0, 1.0, 1.0)
    assert all(np.isnan(A.bootstrap_acc([], [], reps=10)))


def test_bootstrap_mean_clusters_items():
    d = np.array([1.0] * 5 + [0.0] * 15)
    m, lo, hi = A.bootstrap_mean(d, reps=4000)
    assert m == pytest.approx(0.25)
    assert lo > 0 and hi < 0.6


# ---------------------------------------------------------------- Holm

def test_holm_known_values():
    # Classic example: p = [0.01, 0.04, 0.03, 0.005], m = 4
    adj = A.holm([0.01, 0.04, 0.03, 0.005])
    assert adj == pytest.approx([0.03, 0.06, 0.06, 0.02])


def test_holm_monotone_and_capped():
    adj = A.holm([0.5, 0.9, 0.001])
    assert adj[2] == pytest.approx(0.003)
    assert adj.max() <= 1.0
    assert A.holm([]).size == 0


# ---------------------------------------------------------------- paired test / ceiling

def _series(vals):
    return pd.Series(vals, index=[f"i{k}" for k in range(len(vals))], dtype=float)


def test_ceiling_all_zero_differences_does_not_crash():
    r = A.paired_test(_series([1.0] * 20), _series([1.0] * 20), reps=200)
    assert r["p"] == 1.0 and r["note"] == "no difference (ceiling)"
    assert r["delta"] == 0 and r["ci_lo"] == 0 and r["ci_hi"] == 0


def test_floor_and_mid_zero_differences():
    assert A.paired_test(_series([0.0] * 5), _series([0.0] * 5), reps=50)["note"] == "no difference (floor)"
    assert A.paired_test(_series([0.5] * 5), _series([0.5] * 5), reps=50)["note"] == "no difference"


def test_paired_test_detects_large_effect():
    base = _series([0.0] * 18 + [1.0] * 2)
    high = _series([1.0] * 20)
    r = A.paired_test(base, high, reps=1000)
    assert r["delta"] == pytest.approx(0.9)
    assert r["p"] < 0.001 and r["ci_lo"] > 0.7


def test_paired_test_pairs_by_item_only():
    base = pd.Series({"a": 1.0, "b": 0.0, "c": 1.0})
    high = pd.Series({"a": 1.0, "b": 1.0})              # item c missing at high
    r = A.paired_test(base, high, reps=100)
    assert r["n_items"] == 2 and r["delta"] == pytest.approx(0.5)


# ---------------------------------------------------------------- pipeline on synthetic run files

def _run_file(path, model, level, recs):
    sub = [{"results": [{"dictResult": r}]} for r in recs]
    d = {"taskVersion": {"name": f"dial-{level}"}, "modelVersion": {"slug": model},
         "state": "BENCHMARK_TASK_RUN_STATE_COMPLETED",
         "results": [{"numericResult": {"value": 1.0}}], "subruns": sub}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(d), encoding="utf-8")


def _rec(item, fam, level, rep, outcome, tokens, error=None):
    return {"item_id": item, "family": fam, "level": level, "repeat": rep, "probe": 0,
            "expected": "5", "raw": None if outcome == "api_error" else f"x\nFINAL ANSWER: 5 {rep}",
            "parsed": "5" if outcome == "correct" else None,
            "lenient_parsed": "5" if outcome == "correct" else None, "outcome": outcome,
            "output_tokens": None if outcome == "api_error" else tokens, "input_tokens": 100,
            "cost_nanodollars": None if outcome == "api_error" else tokens * 1000,
            "trace_chars": 0, "latency_s": 1.0, "error": error}


def test_pipeline_ceiling_superseded_and_quota(tmp_path):
    res = tmp_path / "main"
    items = [(f"{fam}-{i:03d}", fam) for fam in A.FAMILIES for i in range(4)]
    tok = {"none": 100, "low": 100, "medium": 104, "high": 300}
    # Model at ceiling everywhere, honoring the dial except none~low collapse.
    for lv in A.LEVELS:
        recs = [_rec(it, fam, lv, r, "correct", tok[lv]) for it, fam in items for r in (0, 1)]
        _run_file(res / f"dial-{lv}" / "1" / "haiku" / f"100{lv}" / "x.run.json",
                  "anthropic/claude-haiku-5-5", lv, recs)
    # gpt-oss: low/medium/high only, one level with quota 403s mixed in.
    for lv in ["low", "medium", "high"]:
        recs = [_rec(it, fam, lv, r, "correct" if r == 0 else "wrong", 50 * (1 + A.LEVELS.index(lv)))
                for it, fam in items for r in (0, 1)]
        if lv == "medium":
            recs[0] = _rec(items[0][0], items[0][1], lv, 0, "api_error", 0,
                           error="PermissionDeniedError: ... exceeds your available quota ...")
        _run_file(res / f"dial-{lv}" / "1" / "oss" / f"200{lv}" / "x.run.json",
                  "openai/gpt-oss-120b", lv, recs)
    # A superseded run that would otherwise be "incomplete".
    _run_file(res / "dial-none" / "1" / "mini" / "999" / "x.run.json", "openai/gpt-5.4-mini-2026-03-17",
              "none", [_rec(it, fam, "none", 0, "correct", 10) for it, fam in items])
    sup = tmp_path / "superseded.json"
    sup.write_text(json.dumps({"runs": {"999": "test"}}), encoding="utf-8")

    out = A.run(res, tmp_path / "calls.csv", tmp_path / "summary.md", tmp_path / "figs", sup, reps=200)

    assert (tmp_path / "calls.csv").exists() and (tmp_path / "summary.md").exists()
    assert len(list((tmp_path / "figs").glob("fig*.png"))) == 5
    comp = out["comp"].set_index("model")
    assert comp.loc["openai/gpt-5.4-mini-2026-03-17", "status"] == "superseded, pending re-run"
    assert comp.loc["anthropic/claude-sonnet-5@default", "status"] == "not run yet"
    assert comp.loc["openai/gpt-oss-120b", "missing_quota"] == 1
    tests = out["tests"]
    haiku = tests[tests["model"] == "anthropic/claude-haiku-5-5"]
    assert set(haiku["note"]) == {"no difference (ceiling)"}
    oss = tests[tests["model"] == "openai/gpt-oss-120b"]
    assert set(oss["baseline"]) == {"low"}
    assert tests.loc[tests["model"] == "openai/gpt-5.4-mini-2026-03-17"].empty
    dial = out["dial"].set_index("model")
    assert dial.loc["anthropic/claude-haiku-5-5", "label"] == "honors"
    assert "none~low" in dial.loc["anthropic/claude-haiku-5-5", "collapsed"]
    assert dial.loc["openai/gpt-oss-120b", "rejects"] == "-"         # quota 403 is not a rejection
    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert "no difference (ceiling)" in summary and "superseded" in summary
