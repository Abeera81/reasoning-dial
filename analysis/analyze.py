"""Reasoning Dial analysis (M6). Follows docs/PREREGISTRATION.md §6.

    python analysis/analyze.py

Rebuilds from raw run files in results/main/:
  results/calls.csv, results/summary.md, analysis/figures/fig1..fig5 *.png

Per-call records come from subruns[].results[0].dictResult. Runs listed in
results/superseded.json are loaded into calls.csv (flagged) but excluded from
every statistic. Quota refusals (HTTP 403 "exceeds your available quota") are
missing data, never model behaviour.
"""

import argparse
import glob
import hashlib
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LEVELS = ["none", "low", "medium", "high"]
FAMILIES = ["deduce", "arith", "distract"]
FAMILY_ROLE = {"deduce": "H3 test", "distract": "H2 test", "arith": "H4 control (not H3)"}

# Pre-registered lineup (PREREGISTRATION §4), in display order.
LINEUP = [
    "openai/gpt-oss-120b",
    "openai/gpt-5.4-mini-2026-03-17",
    "anthropic/claude-haiku-5-5",
    "anthropic/claude-sonnet-5@default",
    "google/gemini-3.7-flash",
]
SHORT = {
    "openai/gpt-oss-120b": "gpt-oss-120b",
    "openai/gpt-5.4-mini-2026-03-17": "gpt-5.4-mini",
    "anthropic/claude-haiku-5-5": "claude-haiku-5.5",
    "anthropic/claude-sonnet-5@default": "claude-sonnet-5",
    "google/gemini-3.7-flash": "gemini-3.7-flash",
}
EXPECTED_LEVELS = {"openai/gpt-oss-120b": ["low", "medium", "high"]}  # others: all 4
# Dropped after the lock, before any main-run data existed (logged in MEMORY.md and
# docs/PREREGISTRATION.md §10): per-call quota reservation ~$1.28 x 8 parallel > $10/day.
DROPPED = {"anthropic/claude-sonnet-5@default": "dropped (platform quota reservation)"}
BASELINE = {"openai/gpt-oss-120b": "low"}                              # others: none
# Okabe-Ito colorblind-safe palette, one fixed color + marker per model. The four
# lineup models get four well-separated hues (orange, reddish purple, green, blue);
# gpt-5.4-mini's color is reserved even while its data is pending.
COLORS = {
    "openai/gpt-oss-120b": "#E69F00",
    "openai/gpt-5.4-mini-2026-03-17": "#CC79A7",
    "anthropic/claude-haiku-5-5": "#009E73",
    "anthropic/claude-sonnet-5@default": "#999999",
    "google/gemini-3.7-flash": "#0072B2",
}
MARKERS = {m: mk for m, mk in zip(LINEUP, ["o", "s", "^", "D", "v"])}
OTHER_COLOR = "#999999"

QUOTA_RE = re.compile(r"exceeds your available quota", re.I)
N_BOOT = 5000
SEED = 0
ALPHA = 0.05

# Conservative choices where the pre-registration is silent (also written to summary.md).
CHOICES = [
    "Wilcoxon signed-rank uses zero_method='zsplit' (zero differences stay in the ranking, "
    "split between signs), two-sided. This is more conservative than discarding zeros.",
    "The Holm family is every computed model x family test, Arith included, and tests at "
    "ceiling count with p = 1. Models without complete data are not tested and do not enter "
    "the Holm family; its size m is stated in the header.",
    "Accuracy and the paired difference use only graded calls (correct / wrong / "
    "format_fail). Items with no graded call at a level are dropped from that pair.",
    "Dial labels pool all three families. 'collapsed levels': |median(b) - median(a)| <= "
    "5% of median(a), where a is the lower level. 'rejects': every call at that level is a "
    "non-quota api_error. Partial api_errors are reported but do not set the label.",
    "A model whose high/baseline ratio is >= 1.15 but which fails the 'honors' rule is "
    "labelled 'neither (intermediate)' rather than forced into a label.",
    "Cost per correct = total cost of all non-missing calls / number of correct calls. "
    "It is undefined when there are 0 correct calls.",
]


# ---------------------------------------------------------------- loading

def load_superseded(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("runs", {})


def load_calls(results_dir: Path, superseded: dict) -> pd.DataFrame:
    rows = []
    for f in sorted(glob.glob(str(results_dir / "**" / "*.run.json"), recursive=True)):
        d = json.load(open(f, encoding="utf-8"))
        run_id = Path(f).parent.name
        model = d["modelVersion"]["slug"]
        task = d["taskVersion"]["name"]
        for s in d.get("subruns", []):
            r = (s.get("results") or [{}])[0].get("dictResult")
            if not r:
                continue
            rows.append({**r, "model": model, "task": task, "run_id": run_id,
                         "file": str(Path(f).relative_to(results_dir.parent)
                                     if results_dir.parent in Path(f).parents else f),
                         "superseded": run_id in superseded})
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    for col in ["repeat", "probe"]:
        df[col] = df[col].astype(float).astype(int)
    for col in ["output_tokens", "input_tokens", "cost_nanodollars", "trace_chars", "latency_s"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["cost_usd"] = df["cost_nanodollars"] / 1e9
    err = df["error"].fillna("")
    df["quota_refusal"] = (df["outcome"] == "api_error") & err.str.contains(QUOTA_RE)
    df["status"] = np.where(df["quota_refusal"], "missing", df["outcome"])
    df["graded"] = df["status"].isin(["correct", "wrong", "format_fail"])
    df["correct"] = (df["status"] == "correct").astype(int)
    df["lenient_correct"] = [
        int(_lenient_ok(lp, exp, fam)) if g else 0
        for lp, exp, fam, g in zip(df["lenient_parsed"], df["expected"], df["family"], df["graded"])
    ]
    return df


def _lenient_ok(lenient, expected, family) -> bool:
    if lenient is None or (isinstance(lenient, float) and np.isnan(lenient)):
        return False
    if family == "deduce":
        return str(lenient).lower() == str(expected).lower()
    try:
        return int(str(lenient)) == int(str(expected))
    except ValueError:
        return False


# ---------------------------------------------------------------- statistics

def item_table(df: pd.DataFrame, value: str = "correct") -> pd.DataFrame:
    """Per item: number of graded calls and number correct."""
    g = df[df["graded"]].groupby("item_id")[value].agg(["sum", "count"])
    return g.rename(columns={"sum": "c", "count": "n"})


def bootstrap_acc(c, n, reps: int = N_BOOT, seed: int = SEED):
    """Item-cluster bootstrap: resample items, keep all their calls. Returns (acc, lo, hi)."""
    c, n = np.asarray(c, float), np.asarray(n, float)
    if len(c) == 0 or n.sum() == 0:
        return (np.nan, np.nan, np.nan)
    acc = c.sum() / n.sum()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(c), size=(reps, len(c)))
    boot = c[idx].sum(1) / n[idx].sum(1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return (acc, lo, hi)


def bootstrap_mean(d, reps: int = N_BOOT, seed: int = SEED):
    """Bootstrap the mean of per-item paired differences. Returns (mean, lo, hi)."""
    d = np.asarray(d, float)
    if len(d) == 0:
        return (np.nan, np.nan, np.nan)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(reps, len(d)))
    boot = d[idx].mean(1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return (d.mean(), lo, hi)


def holm(pvals):
    """Holm step-down adjusted p-values (same order as input)."""
    p = np.asarray(pvals, float)
    m = len(p)
    if m == 0:
        return np.array([])
    order = np.argsort(p)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[i]))
        adj[i] = running
    return adj


def paired_test(base: pd.Series, high: pd.Series, reps: int = N_BOOT) -> dict:
    """base/high: per-item mean correctness, indexed by item_id. Pairs by item."""
    both = pd.concat([base.rename("b"), high.rename("h")], axis=1).dropna()
    d = (both["h"] - both["b"]).to_numpy()
    delta, lo, hi = bootstrap_mean(d, reps=reps)
    out = {"n_items": len(d), "acc_base": both["b"].mean() if len(d) else np.nan,
           "acc_high": both["h"].mean() if len(d) else np.nan,
           "delta": delta, "ci_lo": lo, "ci_hi": hi}
    if len(d) == 0:
        return {**out, "p": np.nan, "note": "no paired items"}
    if np.all(d == 0):
        b = both["b"].mean()
        note = "no difference (ceiling)" if b == 1.0 else ("no difference (floor)" if b == 0.0
                                                           else "no difference")
        return {**out, "p": 1.0, "note": note}
    res = stats.wilcoxon(d, zero_method="zsplit", alternative="two-sided")
    return {**out, "p": float(res.pvalue), "note": ""}


# ---------------------------------------------------------------- analysis tables

def model_levels(model):
    return EXPECTED_LEVELS.get(model, LEVELS)


def completeness(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for m in LINEUP + sorted(set(df["model"]) - set(LINEUP)) if len(df) else LINEUP:
        exp = model_levels(m)
        sub = df[(df["model"] == m)] if len(df) else df
        live = sub[~sub["superseded"]] if len(sub) else sub
        have = [lv for lv in exp if len(live) and (live[live["level"] == lv]["graded"]).any()]
        n_sup = int(sub["superseded"].sum()) if len(sub) else 0
        n_missing = int((live["status"] == "missing").sum()) if len(live) else 0
        if m in DROPPED and not have:
            status = DROPPED[m]
        elif not have:
            status = "superseded, pending re-run" if n_sup else "not run yet"
        elif len(have) < len(exp):
            status = "incomplete"
        else:
            status = "complete"
        rows.append({"model": m, "expected_levels": ",".join(exp), "levels_with_data": ",".join(have),
                     "status": status, "graded_calls": int(live["graded"].sum()) if len(live) else 0,
                     "missing_quota": n_missing, "superseded_calls": n_sup})
    return pd.DataFrame(rows)


def accuracy_table(live: pd.DataFrame, reps=N_BOOT) -> pd.DataFrame:
    rows = []
    for (m, fam, lv), g in live.groupby(["model", "family", "level"]):
        it = item_table(g)
        acc, lo, hi = bootstrap_acc(it["c"], it["n"], reps=reps)
        itl = item_table(g, "lenient_correct")
        lacc = itl["c"].sum() / itl["n"].sum() if len(itl) else np.nan
        rows.append({"model": m, "family": fam, "level": lv, "n_calls": int(g["graded"].sum()),
                     "n_items": len(it), "acc": acc, "ci_lo": lo, "ci_hi": hi, "acc_lenient": lacc,
                     "format_fail": int((g["status"] == "format_fail").sum()),
                     "api_error": int((g["status"] == "api_error").sum()),
                     "missing": int((g["status"] == "missing").sum())})
    return pd.DataFrame(rows)


def delta_tests(live: pd.DataFrame, comp: pd.DataFrame, reps=N_BOOT) -> pd.DataFrame:
    rows = []
    status = dict(zip(comp["model"], comp["status"]))
    for m in [x for x in LINEUP if x in set(live["model"])] + sorted(set(live["model"]) - set(LINEUP)):
        base_lv = BASELINE.get(m, "none")
        for fam in FAMILIES:
            row = {"model": m, "family": fam, "role": FAMILY_ROLE[fam], "baseline": base_lv}
            if status.get(m) != "complete":
                rows.append({**row, "note": f"not tested ({status.get(m)})", "p": np.nan})
                continue
            g = live[(live["model"] == m) & (live["family"] == fam) & live["graded"]]
            per = g.groupby(["level", "item_id"])["correct"].mean()
            base = per.get(base_lv, pd.Series(dtype=float))
            high = per.get("high", pd.Series(dtype=float))
            rows.append({**row, **paired_test(base, high, reps=reps)})
    out = pd.DataFrame(rows)
    tested = out["p"].notna()
    out["p_holm"] = np.nan
    out.loc[tested, "p_holm"] = holm(out.loc[tested, "p"].to_numpy())
    out["effect"] = tested & (out["p_holm"] < ALPHA) & ((out["ci_lo"] > 0) | (out["ci_hi"] < 0))
    out["m_holm"] = int(tested.sum())
    return out


def dial_labels(live: pd.DataFrame, comp: pd.DataFrame) -> pd.DataFrame:
    rows = []
    status = dict(zip(comp["model"], comp["status"]))
    for m in [x for x in LINEUP if x in set(live["model"])]:
        exp = model_levels(m)
        g = live[live["model"] == m]
        ok = g[g["status"].isin(["correct", "wrong", "format_fail"]) & g["output_tokens"].notna()]
        med = {lv: ok[ok["level"] == lv]["output_tokens"].median() for lv in exp}
        tr = {lv: ok[ok["level"] == lv]["trace_chars"].median() for lv in exp}
        n = {lv: int((ok["level"] == lv).sum()) for lv in exp}
        rejects = [lv for lv in exp if len(g[g["level"] == lv])
                   and (g[g["level"] == lv]["status"] == "api_error").all()]
        partial_err = {lv: int((g[g["level"] == lv]["status"] == "api_error").sum()) for lv in exp}
        base = BASELINE.get(m, "none")
        vals = [med[lv] for lv in exp]
        if status.get(m) != "complete" or any(pd.isna(v) for v in vals):
            label, ratio, collapsed = f"not labelled ({status.get(m)})", np.nan, []
        else:
            ratio = med["high"] / med[base] if med[base] else np.nan
            monotone = all(b >= a for a, b in zip(vals, vals[1:]))
            if monotone and ratio >= 1.3:
                label = "honors"
            elif ratio < 1.15:
                label = "ignores"
            else:
                label = "neither (intermediate)"
            collapsed = [f"{a}~{b}" for a, b in zip(exp, exp[1:])
                         if abs(med[b] - med[a]) <= 0.05 * med[a]]
        notes = []
        if m == "openai/gpt-oss-120b":
            notes.append("rejects none (HTTP 400, calibration; not run in main by design)")
        rows.append({"model": m, **{f"med_{lv}": med.get(lv, np.nan) for lv in LEVELS},
                     **{f"n_{lv}": n.get(lv, 0) for lv in LEVELS},
                     **{f"trace_{lv}": tr.get(lv, np.nan) for lv in LEVELS},
                     "baseline": base, "ratio_high_base": ratio, "label": label,
                     "collapsed": ", ".join(collapsed) or "-",
                     "rejects": ", ".join(rejects) or "-",
                     "api_errors": ", ".join(f"{k}:{v}" for k, v in partial_err.items() if v) or "-",
                     "notes": "; ".join(notes)})
    return pd.DataFrame(rows)


def cost_table(live: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (m, fam, lv), g in live.groupby(["model", "family", "level"]):
        g = g[g["status"] != "missing"]
        n_correct = int(g["correct"].sum())
        total = float(g["cost_usd"].fillna(0).sum())
        rows.append({"model": m, "family": fam, "level": lv, "n_calls": len(g), "n_correct": n_correct,
                     "total_cost": total, "mean_cost_call": total / len(g) if len(g) else np.nan,
                     "cost_per_correct": total / n_correct if n_correct else np.nan})
    return pd.DataFrame(rows)


def noise_table(live: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (m, fam, lv), g in live.groupby(["model", "family", "level"]):
        gg = g[g["graded"]]
        per_rep = gg.groupby("repeat")["correct"].mean()
        piv = gg.pivot_table(index="item_id", columns="repeat", values="correct", aggfunc="first")
        both = piv.dropna()
        flips = int((both.nunique(axis=1) > 1).sum()) if len(both) else 0
        raw = g[g["status"] != "missing"].pivot_table(index="item_id", columns="repeat",
                                                     values="raw", aggfunc="first")
        if raw.shape[1] > 1:
            ident_mask = (raw.nunique(axis=1, dropna=True) == 1) & (raw.notna().sum(axis=1) > 1)
        else:
            ident_mask = pd.Series(False, index=raw.index)
        ident = int(ident_mask.sum())
        ident_chars = raw[ident_mask].iloc[:, 0].str.len().median() if ident else np.nan
        tok = g[g["status"] != "missing"].pivot_table(index="item_id", columns="repeat",
                                                     values="output_tokens", aggfunc="first")
        tok_pairs = tok.dropna()
        same_tok = int((tok_pairs.nunique(axis=1) == 1).sum()) if tok.shape[1] > 1 else 0
        rows.append({"model": m, "family": fam, "level": lv,
                     "acc_by_repeat": " / ".join(f"{v:.2f}" for v in per_rep.to_numpy()),
                     "range": float(per_rep.max() - per_rep.min()) if len(per_rep) else np.nan,
                     "items_paired": len(both), "flips": flips,
                     "flip_rate": flips / len(both) if len(both) else np.nan,
                     "byte_identical_repeats": ident,
                     "identical_reply_chars": ident_chars,
                     "token_pairs": len(tok_pairs),
                     "identical_output_tokens": same_tok})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- figures
# Presentation only: nothing below changes a statistic. Every figure is saved twice:
# analysis/figures/<name> with the full footer, analysis/figures/article/<name> with a
# one-line footer for the article.

FAMILY_TITLE = {"deduce": "Logic puzzles (Deduce)", "arith": "Arithmetic, control (Arith)",
                "distract": "Counting with distractors (Distract)"}
FAMILY_WORD = {"deduce": "logic", "arith": "arithmetic", "distract": "counting"}
FAMILY_MARKER = {"deduce": "o", "arith": "s", "distract": "^"}
TINY = {"openai/gpt-oss-120b": "gpt-oss", "openai/gpt-5.4-mini-2026-03-17": "gpt-5.4-mini",
        "anthropic/claude-haiku-5-5": "haiku-5.5", "google/gemini-3.7-flash": "gemini-3.7-flash",
        "anthropic/claude-sonnet-5@default": "sonnet-5"}
# Levels a model cannot run, shown in tables/figures instead of "no data".
REJECTED_LEVELS = {"openai/gpt-oss-120b": {"none": "rejects ‘none’"}}


def _color(m):
    return COLORS.get(m, OTHER_COLOR)


def _short(m):
    return SHORT.get(m, m)


def _setup():
    plt.rcParams.update({"font.size": 13, "axes.titlesize": 15, "axes.labelsize": 13,
                         "legend.fontsize": 12, "figure.dpi": 100})


def _plot_models(present):
    return [m for m in LINEUP if m in present]


def _token_axis(ax):
    """Log y axis with plain-number labels: 50, 100, 200, 500, 1,000, ..."""
    from matplotlib.ticker import FixedLocator, FuncFormatter, NullFormatter, NullLocator
    lo, hi = ax.get_ylim()
    ticks = [v for d in range(0, 7) for v in (1 * 10 ** d, 2 * 10 ** d, 5 * 10 ** d) if lo <= v <= hi]
    ax.yaxis.set_major_locator(FixedLocator(ticks))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_minor_formatter(NullFormatter())


def _cost_axis(ax):
    """Log y axis with dollar labels at decades: $0.0001, $0.001, $0.01, ..."""
    from matplotlib.ticker import FixedLocator, FuncFormatter, NullFormatter, NullLocator
    lo, hi = ax.get_ylim()
    ticks = [10.0 ** e for e in range(-7, 2) if lo <= 10.0 ** e <= hi]
    ax.yaxis.set_major_locator(FixedLocator(ticks))
    ax.yaxis.set_major_formatter(FuncFormatter(
        lambda v, _: "$" + np.format_float_positional(v, trim="-")))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_minor_formatter(NullFormatter())


def _times_axis(ax):
    """Log x axis labelled ×1, ×2, ×5, ×10, ×20, ..."""
    from matplotlib.ticker import FixedLocator, FuncFormatter, NullFormatter, NullLocator
    lo, hi = ax.get_xlim()
    ticks = [v for v in (0.5, 1, 2, 5, 10, 20, 50, 100, 200) if lo <= v <= hi]
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"×{v:g}"))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_minor_formatter(NullFormatter())


def _save(fig, fig_dir: Path, name: str, full: str, short: str, rect=(0, 0.06, 1, 0.95)):
    """Save with the full footer, then an article/ copy with a one-line footer."""
    import textwrap
    footer = fig.text(0.01, 0.01, "\n".join(textwrap.wrap(full, 190)), fontsize=11, ha="left",
                      va="bottom", color="#333333")
    fig.tight_layout(rect=rect)
    fig.savefig(fig_dir / name)
    footer.set_text(short)
    (fig_dir / "article").mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_dir / "article" / name)
    plt.close(fig)


def _dodge(models):
    """x offsets so models sharing a value stay visible side by side."""
    k = len(models)
    return {m: (i - (k - 1) / 2) * 0.07 for i, m in enumerate(models)}


def fig_dial_curves(acc, fig_dir, full, short):
    fig, axes = plt.subplots(1, 3, figsize=(16, 6.2), sharey=True)
    models = _plot_models(set(acc["model"]))
    off = _dodge(models)
    for ax, fam in zip(axes, FAMILIES):
        for m in models:
            a = acc[(acc["model"] == m) & (acc["family"] == fam)].set_index("level")
            lvls = [lv for lv in LEVELS if lv in a.index]
            if not lvls:
                continue
            x = [LEVELS.index(lv) + off[m] for lv in lvls]
            ax.plot(x, a.loc[lvls, "acc"], marker=MARKERS.get(m, "o"), color=_color(m),
                    label=_short(m), lw=2.2, ms=8)
            ax.fill_between(x, a.loc[lvls, "ci_lo"], a.loc[lvls, "ci_hi"], color=_color(m), alpha=0.15)
        ax.set_title(FAMILY_TITLE[fam])
        if fam == "deduce":
            # Deduce answers are one of 7 names, so blind guessing scores 1/7.
            ax.axhline(1 / 7, color="#888888", ls="--", lw=1.4, zorder=0)
            ax.text(3.15, 1 / 7 + 0.02, "random guess (1 in 7 names)", ha="right", va="bottom",
                    fontsize=11, color="#555555")
        ax.set_xticks(range(4), LEVELS)
        ax.set_xlabel("reasoning effort")
        ax.set_ylim(-0.02, 1.06)
        ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("accuracy")
    axes[-1].legend(loc="lower right")
    fig.suptitle("Fig 1. Accuracy at each reasoning-effort level (shaded: 95% confidence interval)")
    _save(fig, fig_dir, "fig1_dial_curves.png", full, short)


def _clean_label(label: str) -> str:
    return "intermediate" if label.startswith("neither") else label


def fig_token_ladder(dial, fig_dir, full, short):
    fig, ax = plt.subplots(figsize=(16, 7))
    for _, r in dial.iterrows():
        lvls = [lv for lv in LEVELS if not pd.isna(r[f"med_{lv}"])]
        if not lvls:
            continue
        x = [LEVELS.index(lv) for lv in lvls]
        y = [r[f"med_{lv}"] for lv in lvls]
        ax.plot(x, y, marker=MARKERS.get(r["model"], "o"), color=_color(r["model"]), lw=2.2, ms=9,
                label=f"{_short(r['model'])}: {_clean_label(r['label'])}")
    ax.set_yscale("log")
    _token_axis(ax)
    ax.set_xticks(range(4), LEVELS)
    ax.set_xlabel("reasoning effort")
    ax.set_ylabel("median output tokens per answer")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left")
    fig.suptitle("Fig 2. Median output tokens by dial level (all three task types together)")
    _save(fig, fig_dir, "fig2_token_ladder.png", full, short)


def fig_token_ladder_by_family(explore, fig_dir, full, short):
    fig, axes = plt.subplots(1, 3, figsize=(16, 6.2), sharey=True)
    models = _plot_models(set(explore["model"]))
    for ax, fam in zip(axes, FAMILIES):
        for m in models:
            r = explore[(explore["model"] == m) & (explore["family"] == fam)]
            if r.empty:
                continue
            r = r.iloc[0]
            lvls = [lv for lv in LEVELS if not pd.isna(r[f"med_{lv}"])]
            ax.plot([LEVELS.index(lv) for lv in lvls], [r[f"med_{lv}"] for lv in lvls],
                    marker=MARKERS.get(m, "o"), color=_color(m), label=_short(m), lw=2.2, ms=8)
        ax.set_yscale("log")
        ax.set_title(FAMILY_TITLE[fam])
        ax.set_xticks(range(4), LEVELS)
        ax.set_xlabel("reasoning effort")
        ax.grid(alpha=0.3)
    for ax in axes:
        _token_axis(ax)
    axes[0].set_ylabel("median output tokens per answer")
    axes[0].legend(loc="upper left")
    fig.suptitle("Median output tokens by dial level (exploratory, not pre-registered)")
    _save(fig, fig_dir, "fig2b_token_ladder_by_family.png", full, short)


def fig_cost_per_correct(cost, fig_dir, full, short):
    fig, axes = plt.subplots(1, 3, figsize=(16, 6.2), sharey=True)
    models = _plot_models(set(cost["model"]))
    for ax, fam in zip(axes, FAMILIES):
        for m in models:
            c = cost[(cost["model"] == m) & (cost["family"] == fam)].set_index("level")
            lvls = [lv for lv in LEVELS if lv in c.index and not pd.isna(c.loc[lv, "cost_per_correct"])]
            if not lvls:
                continue
            ax.plot([LEVELS.index(lv) for lv in lvls], c.loc[lvls, "cost_per_correct"],
                    marker=MARKERS.get(m, "o"), color=_color(m), label=_short(m), lw=2.2, ms=8)
        ax.set_yscale("log")
        ax.set_title(FAMILY_TITLE[fam])
        ax.set_xticks(range(4), LEVELS)
        ax.set_xlabel("reasoning effort")
        ax.grid(alpha=0.3)
    for ax in axes:
        _cost_axis(ax)
    axes[0].set_ylabel("cost per correct answer (USD)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=len(labels), bbox_to_anchor=(0.5, 0.935),
               frameon=False)
    fig.suptitle("Fig 3. Cost per correct answer at each reasoning-effort level")
    _save(fig, fig_dir, "fig3_cost_per_correct.png", full, short, rect=(0, 0.06, 1, 0.89))


def fig_forest(tests, fig_dir, full, short):
    t = tests.copy()
    t["label"] = [f"{_short(m)} · {FAMILY_WORD[fam]} · high − {b}"
                  for m, fam, b in zip(t["model"], t["family"], t["baseline"])]
    h = max(4, 0.55 * len(t) + 2.2)
    fig, ax = plt.subplots(figsize=(16, h))
    for i, r in enumerate(t.itertuples()):
        y = len(t) - 1 - i
        if pd.isna(r.p):
            ax.text(0, y, r.note, va="center", ha="center", fontsize=11, color="#666666")
            continue
        ax.errorbar(r.delta * 100, y, xerr=[[(r.delta - r.ci_lo) * 100], [(r.ci_hi - r.delta) * 100]],
                    fmt=MARKERS.get(r.model, "o"), color=_color(r.model), ms=9, capsize=5, lw=2)
        tag = r.note or ("effect" if r.effect else "no effect")
        ax.text(1.02, y, f"{tag}; n={r.n_items} questions; Holm p={r.p_holm:.3g}",
                va="center", fontsize=10, transform=ax.get_yaxis_transform())
    ax.axvline(0, color="black", lw=1)
    ax.set_yticks(range(len(t)), list(reversed(t["label"].tolist())))
    span = np.nanmax(np.abs(t[["ci_lo", "ci_hi"]].to_numpy(float))) * 100 if t["p"].notna().any() else 50
    lim = max(40, span + 10)
    ax.set_xlim(-lim, lim)
    ax.set_xlabel("change in accuracy, percentage points (high − lowest level), 95% CI")
    ax.grid(alpha=0.3, axis="x")
    fig.suptitle("Fig 4. Change in accuracy when the dial goes from the lowest level to high")
    _save(fig, fig_dir, "fig4_forest_delta.png", full, short, rect=(0, 0.07, 0.74, 0.96))


def fig_format(acc, fig_dir, full, short):
    models = _plot_models(set(acc["model"]))
    agg = acc.groupby(["model", "level"])[["format_fail", "n_calls"]].sum()
    mat = np.full((len(models), 4), np.nan)
    ann = [["" for _ in LEVELS] for _ in models]
    for i, m in enumerate(models):
        for j, lv in enumerate(LEVELS):
            if (m, lv) in agg.index and agg.loc[(m, lv), "n_calls"] > 0:
                ff, n = agg.loc[(m, lv)]
                mat[i, j] = ff / n
                ann[i][j] = f"{ff / n:.1%}\n{int(ff)}/{int(n)}"
            else:
                ann[i][j] = REJECTED_LEVELS.get(m, {}).get(lv, "no data")
    fig, ax = plt.subplots(figsize=(16, 1.2 * len(models) + 2.6))
    vmax = max(0.1, np.nanmax(mat)) if np.isfinite(mat).any() else 0.1
    im = ax.imshow(np.nan_to_num(mat, nan=0), cmap="Greys", vmin=0, vmax=vmax, aspect="auto")
    for i in range(len(models)):
        for j in range(4):
            v = mat[i, j]
            ax.text(j, i, ann[i][j], ha="center", va="center", fontsize=12,
                    color="white" if (not np.isnan(v) and v > 0.06) else "black")
    ax.set_xticks(range(4), LEVELS)
    ax.set_yticks(range(len(models)), [_short(m) for m in models])
    for tick, m in zip(ax.get_yticklabels(), models):
        tick.set_color(_color(m))
    fig.colorbar(im, ax=ax, label="share of answers without a usable FINAL ANSWER line",
                 format=matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    fig.suptitle("Fig 5. Format failures (no parseable FINAL ANSWER line) by model and level")
    _save(fig, fig_dir, "fig5_format_failures.png", full, short, rect=(0, 0.07, 1, 0.94))


def _place_note(fig, ax, anchor, text, bars, legends):
    """Semi-transparent note for the zero-change cluster, placed where it overlaps no error bar.

    `bars` are (x, y, lo, hi) in data units. Tries offsets below/above the anchor, then free spots
    along the axes edges; keeps the first box inside the axes that touches no error bar (incl. caps
    and marker) and no legend. Falls back to the least-overlapping candidate.
    """
    from matplotlib.transforms import Bbox
    renderer = fig.canvas.get_renderer()
    to_px = ax.transData.transform
    obstacles = []
    for x, y, lo, hi in bars:
        (x0, y0), (x1, y1) = to_px([(x, lo), (x, hi)])
        obstacles.append(Bbox([[x0 - 10, y0 - 10], [x1 + 10, y1 + 10]]))
    obstacles += [lg.get_window_extent(renderer).padded(4) for lg in legends]
    axbox = ax.get_window_extent(renderer)
    style = {"fontsize": 11, "color": "#333333", "zorder": 5,
             "bbox": {"boxstyle": "round,pad=0.3", "fc": "white", "ec": "#bbbbbb", "alpha": 0.7}}
    candidates = [dict(xy=anchor, textcoords="offset points", xytext=(0, dy), ha="center",
                       va="top" if dy < 0 else "bottom") for dy in (-48, -90, 48, 90)]
    candidates += [dict(xy=(fx, fy), xycoords="axes fraction", ha="center", va=va)
                   for fy, va in ((0.03, "bottom"), (0.97, "top")) for fx in (0.5, 0.35, 0.65, 0.8)]
    best = None
    for kw in candidates:
        note = ax.annotate(text, **kw, **style)
        box = note.get_window_extent(renderer).padded(2)
        hits = sum(box.overlaps(o) for o in obstacles)
        inside = axbox.x0 <= box.x0 and box.x1 <= axbox.x1 and axbox.y0 <= box.y0 and box.y1 <= axbox.y1
        score = hits + (0 if inside else 100)
        if best is None or score < best[0]:
            if best is not None:
                best[1].remove()
            best = (score, note)
        else:
            note.remove()
        if score == 0:
            break
    return best[1]


def fig_cost_vs_gain(tests, cost, fig_dir, full, short):
    """Headline: cost multiplier (high ÷ lowest level) vs accuracy change, per model × family."""
    rows = []
    for r in tests[tests["p"].notna()].itertuples():
        c = cost[(cost["model"] == r.model) & (cost["family"] == r.family)].set_index("level")
        if "high" not in c.index or r.baseline not in c.index:
            continue
        hi, lo = c.loc["high", "cost_per_correct"], c.loc[r.baseline, "cost_per_correct"]
        if pd.isna(hi) or pd.isna(lo) or lo <= 0:
            continue
        rows.append((r.model, r.family, hi / lo, r.delta * 100, r.ci_lo * 100, r.ci_hi * 100))
    fig, ax = plt.subplots(figsize=(16, 8))
    from matplotlib.lines import Line2D
    for m, fam, x, y, lo, hi in rows:
        ax.errorbar(x, y, yerr=[[y - lo], [hi - y]], fmt=FAMILY_MARKER[fam], color=_color(m), ms=11,
                    capsize=4, lw=1.6, mec="black", mew=0.6)
    # Label only points off the zero line; summarise the zero-change cluster in one note.
    zero = [r for r in rows if abs(r[3]) < 1e-9]
    for m, fam, x, y, *_ in (r for r in rows if abs(r[3]) >= 1e-9):
        ax.annotate(f"{TINY.get(m, _short(m))} · {FAMILY_WORD[fam]}", (x, y), textcoords="offset points",
                    xytext=(10, 6), fontsize=10, color="#222222")
    ax.axhline(0, color="black", lw=1)
    ax.set_xscale("log")
    zero_note = None
    if zero:
        zx = [r[2] for r in zero]
        a, b = min(zx), max(zx)
        ax.plot([a, b], [0, 0], color="#888888", lw=10, alpha=0.25, solid_capstyle="round", zorder=0)
        zero_note = ((float(np.sqrt(a * b)), 0),
                     f"{len(zero)} of {len(rows)} cases: accuracy unchanged, cost ×{a:.1f}–×{b:.1f}")
    xs = [r[2] for r in rows] or [1, 2]
    ax.set_xlim(min(0.8, min(xs) / 1.3), max(25, max(xs) * 1.6))
    _times_axis(ax)
    # y range adapts to every error bar (plus padding); always keeps room around 0 for the note.
    los = [r[4] for r in rows] or [0]
    his = [r[5] for r in rows] or [0]
    lo_v, hi_v = min(min(los), -15), max(max(his), 15)
    pad = max(5, 0.1 * (hi_v - lo_v))
    ax.set_ylim(lo_v - pad, hi_v + pad)
    ax.set_xlabel("cost per correct answer at high ÷ at the model's lowest level")
    ax.set_ylabel("accuracy change, percentage points (high − lowest)")
    ax.grid(alpha=0.3)
    models = [m for m in LINEUP if m in {r[0] for r in rows}]
    h_models = [Line2D([], [], marker="o", ls="", color=_color(m), ms=10, label=_short(m)) for m in models]
    h_fams = [Line2D([], [], marker=FAMILY_MARKER[f], ls="", color="#777777", mec="black", ms=10,
                     label=FAMILY_TITLE[f]) for f in FAMILIES]
    leg1 = ax.legend(handles=h_models, title="model (color)", loc="upper left")
    ax.add_artist(leg1)
    leg2 = ax.legend(handles=h_fams, title="task type (shape)", loc="lower left")
    fig.suptitle("What turning the reasoning dial to ‘high’ bought")
    if zero_note:
        fig.tight_layout(rect=(0, 0.06, 1, 0.95))  # same rect as _save, so positions are final
        _place_note(fig, ax, *zero_note, bars=[r[2:] for r in rows], legends=[leg1, leg2])
    _save(fig, fig_dir, "fig0_cost_vs_gain.png", full, short)


def fig_cover(tests, cost, fig_dir):
    """DEV cover image, exactly 1000x420 px: title, subtitle and a simplified Fig 0."""
    from matplotlib.lines import Line2D
    rows = []
    for r in tests[tests["p"].notna()].itertuples():
        c = cost[(cost["model"] == r.model) & (cost["family"] == r.family)].set_index("level")
        if "high" not in c.index or r.baseline not in c.index:
            continue
        hi, lo = c.loc["high", "cost_per_correct"], c.loc[r.baseline, "cost_per_correct"]
        if pd.isna(hi) or pd.isna(lo) or lo <= 0:
            continue
        rows.append((r.model, r.family, hi / lo, r.delta * 100, r.acc_base, r.acc_high))

    with plt.rc_context({"font.size": 13}):
        fig = plt.figure(figsize=(10, 4.2), dpi=100, facecolor="white")
        fig.text(0.04, 0.80, "The Reasoning Dial", fontsize=27, fontweight="bold", color="#111111",
                 va="center")
        fig.text(0.04, 0.655, "What turning AI reasoning\nup to ‘high’ actually buys", fontsize=15,
                 color="#444444", va="center", linespacing=1.3)
        fig.text(0.04, 0.485, "Sometimes essential.\nUsually just a bigger bill.", fontsize=14,
                 fontweight="bold", fontstyle="italic", color="#1a1a1a", va="center", linespacing=1.3)
        models = [m for m in LINEUP if m in {r[0] for r in rows}]
        for i, m in enumerate(models):
            y = 0.345 - i * 0.07
            fig.text(0.055, y, "●", fontsize=15, color=_color(m), va="center")
            fig.text(0.085, y, _short(m), fontsize=13, color="#222222", va="center")

        ax = fig.add_axes((0.585, 0.17, 0.39, 0.73))
        for m, fam, x, y, *_ in rows:
            ax.plot(x, y, marker=FAMILY_MARKER[fam], color=_color(m), ms=13, mec="black", mew=0.6,
                    ls="", zorder=3)
        ax.axhline(0, color="#333333", lw=1.2, zorder=1)
        ax.set_xscale("log")
        xs = [r[2] for r in rows] or [1, 2]
        ax.set_xlim(min(0.8, min(xs) / 1.4), max(25, max(xs) * 1.6))
        _times_axis(ax)
        ys = [r[3] for r in rows] or [0]
        ax.set_ylim(min(-25, min(ys) - 10), max(100, max(ys) + 10))
        if rows:
            m, fam, x, y, a0, a1 = max(rows, key=lambda r: r[3])
            pct = lambda v: f"{v * 100:.1f}".rstrip("0").rstrip(".") + "%"  # 0.975 -> 97.5%, 0.15 -> 15%
            ax.annotate(f"{_short(m)} · {FAMILY_WORD[fam]}\n{pct(a0)} → {pct(a1)}", (x, y),
                        textcoords="offset points", xytext=(-14, 0), ha="right", va="center",
                        fontsize=12, color="#111111", linespacing=1.2)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:+.0f}" if v else "0"))
        ax.set_xlabel("cost of a correct answer, high vs lowest", fontsize=12)
        ax.set_ylabel("accuracy change (points)", fontsize=12)
        ax.tick_params(labelsize=12)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.grid(alpha=0.25)
        shapes = [Line2D([], [], marker=FAMILY_MARKER[f], ls="", color="#bbbbbb", mec="black", ms=10,
                         label=FAMILY_WORD[f]) for f in FAMILIES]
        ax.legend(handles=shapes, loc="upper right", fontsize=11, frameon=False, handletextpad=0.2)
        (fig_dir / "article").mkdir(parents=True, exist_ok=True)
        fig.savefig(fig_dir / "article" / "cover.png", dpi=100, facecolor="white")
        plt.close(fig)


# ---------------------------------------------------------------- summary

def _f(x, spec=".2f"):
    return "–" if x is None or (isinstance(x, float) and np.isnan(x)) else format(x, spec)


def md_table(df: pd.DataFrame, cols, fmt=None) -> str:
    fmt = fmt or {}
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if c in fmt:
                v = fmt[c](v)
            elif c == "model":
                v = _short(v)
            cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def explore_tokens(live: pd.DataFrame) -> pd.DataFrame:
    """Exploratory (not pre-registered): median output tokens per model x family x level."""
    rows = []
    ok = live[live["graded"] & live["output_tokens"].notna()]
    for m in [x for x in LINEUP if x in set(ok["model"])]:
        base = BASELINE.get(m, "none")
        for fam in FAMILIES:
            g = ok[(ok["model"] == m) & (ok["family"] == fam)]
            med = {lv: g[g["level"] == lv]["output_tokens"].median() for lv in LEVELS}
            b = med.get(base)
            ratio = med["high"] / b if b and not pd.isna(b) else np.nan
            rows.append({"model": m, "family": fam, **{f"med_{lv}": med[lv] for lv in LEVELS},
                         "ratio_high_base": ratio})
    return pd.DataFrame(rows)


def write_summary(path, *, n_files, superseded, hash_ok, comp, acc, tests, dial, cost, noise, explore):
    L = []
    L.append("# Reasoning Dial — analysis summary\n")
    L.append("Generated by `python analysis/analyze.py` from the raw run files in `results/main/`. "
             "Follows docs/PREREGISTRATION.md §6. Do not edit by hand.\n")
    L.append(f"- Run files read: {n_files}; superseded (excluded): {len(superseded)} "
             f"({', '.join(sorted(superseded)) or 'none'})")
    L.append(f"- Locked test set SHA-256 matches `data/test_items.sha256`: **{hash_ok}**")
    L.append(f"- Bootstrap: item-cluster, {N_BOOT} reps, numpy seed {SEED}. α = {ALPHA}, Holm across "
             f"all computed model × family tests (m = {int(tests['m_holm'].iloc[0]) if len(tests) else 0}).\n")

    L.append("## 1. Completeness\n")
    L.append(md_table(comp, ["model", "expected_levels", "levels_with_data", "status", "graded_calls",
                             "missing_quota", "superseded_calls"]))
    L.append("\nModels that are not complete are reported in the descriptive tables where data exists, "
             "but they are not tested and not labelled.\n")

    L.append("## 2. Accuracy (strict) with 95% item-cluster bootstrap CI\n")
    a = acc.copy()
    a["order"] = a["level"].map(LEVELS.index)
    a = a.sort_values(["model", "family", "order"])
    L.append(md_table(a, ["model", "family", "level", "n_items", "n_calls", "acc", "ci_lo", "ci_hi",
                          "acc_lenient", "format_fail", "api_error", "missing"],
                      {"acc": _f, "ci_lo": _f, "ci_hi": _f, "acc_lenient": _f}))

    L.append("\n## 3. Pre-registered tests: Δ = accuracy(high) − accuracy(baseline), paired by item\n")
    L.append("Effect = Holm-adjusted p < 0.05 **and** bootstrap CI excludes 0. Baseline is `none`, "
             "except gpt-oss-120b (`low`).\n")
    t = tests.copy()
    t["result"] = [
        (r["note"] if r["note"] else ("**effect**" if r["effect"] else "no effect"))
        for _, r in t.iterrows()
    ]
    L.append(md_table(t, ["model", "family", "role", "baseline", "n_items", "acc_base", "acc_high",
                          "delta", "ci_lo", "ci_hi", "p", "p_holm", "result"],
                      {"n_items": lambda v: _f(v, ".0f"), "acc_base": _f, "acc_high": _f,
                       "delta": lambda v: _f(v, "+.3f"), "ci_lo": lambda v: _f(v, "+.3f"),
                       "ci_hi": lambda v: _f(v, "+.3f"), "p": lambda v: _f(v, ".3g"),
                       "p_holm": lambda v: _f(v, ".3g")}))

    L.append("\n## 4. Dial behaviour (H1): median output tokens per level, families pooled\n")
    L.append("Labels: *honors* = medians non-decreasing baseline→high and high/baseline ≥ 1.3; "
             "*ignores* = high/baseline < 1.15; *collapsed levels* = adjacent levels within 5%; "
             "*rejects* = api_error on that level.\n")
    L.append(md_table(dial, ["model", "baseline", "med_none", "med_low", "med_medium", "med_high",
                             "ratio_high_base", "label", "collapsed", "rejects", "api_errors", "notes"],
                      {**{f"med_{lv}": lambda v: _f(v, ".0f") for lv in LEVELS},
                       "ratio_high_base": _f}))
    L.append("\nReasoning-trace length (median characters, partial check; only some providers return traces):\n")
    L.append(md_table(dial, ["model"] + [f"trace_{lv}" for lv in LEVELS],
                      {f"trace_{lv}": lambda v: _f(v, ".0f") for lv in LEVELS}))
    L.append("\nCalls per level used for the medians:\n")
    L.append(md_table(dial, ["model"] + [f"n_{lv}" for lv in LEVELS]))

    L.append("\n## 5. Cost (H4): cost per correct answer (USD)\n")
    c = cost.copy()
    c["order"] = c["level"].map(LEVELS.index)
    c = c.sort_values(["model", "family", "order"])
    L.append(md_table(c, ["model", "family", "level", "n_calls", "n_correct", "total_cost",
                          "mean_cost_call", "cost_per_correct"],
                      {"total_cost": lambda v: _f(v, ".4f"), "mean_cost_call": lambda v: _f(v, ".5f"),
                       "cost_per_correct": lambda v: _f(v, ".5f")}))

    L.append("\n## 6. Format failures: rate per model × level, strict vs lenient accuracy\n")
    f = acc.groupby(["model", "level"]).agg(n_calls=("n_calls", "sum"), format_fail=("format_fail", "sum")).reset_index()
    f["rate"] = f["format_fail"] / f["n_calls"]
    f["order"] = f["level"].map(LEVELS.index)
    f = f.sort_values(["model", "order"])
    L.append(md_table(f, ["model", "level", "n_calls", "format_fail", "rate"], {"rate": lambda v: _f(v, ".1%")}))
    L.append("\n(Strict vs lenient accuracy per cell: columns `acc` and `acc_lenient` in §2.)\n")

    L.append("## 7. Noise floor: repeats\n")
    n = noise.copy()
    n["order"] = n["level"].map(LEVELS.index)
    n = n.sort_values(["model", "family", "order"])
    L.append("Two independence checks per cell. `byte_identical_repeats`: items whose two visible "
             "replies are byte-identical. These occur mainly where the visible reply is only the final "
             "answer line (`identical_reply_chars` = median length of those replies): two independent "
             "calls that both answer correctly print the same short line. They are not evidence of "
             "caching or of seed handling. `identical_output_tokens`: items whose two calls used exactly "
             "the same number of output tokens (hidden reasoning included), out of `token_pairs`. This is "
             "the stronger check: independent generations with reasoning rarely match token-for-token.\n")
    L.append(md_table(n, ["model", "family", "level", "acc_by_repeat", "range", "items_paired", "flips",
                          "flip_rate", "byte_identical_repeats", "identical_reply_chars", "token_pairs",
                          "identical_output_tokens"],
                      {"range": _f, "flip_rate": lambda v: _f(v, ".2f"),
                       "identical_reply_chars": lambda v: _f(v, ".0f")}))

    L.append("\n## 7b. Exploratory (not pre-registered): median output tokens per model × family × level\n")
    L.append("Descriptive only. The pre-registered dial labels in §4 pool all families and are unchanged. "
             "Medians over graded calls; n per cell in §2.\n")
    L.append(md_table(explore, ["model", "family"] + [f"med_{lv}" for lv in LEVELS] + ["ratio_high_base"],
                      {**{f"med_{lv}": (lambda v: _f(v, ".0f")) for lv in LEVELS},
                       "ratio_high_base": _f}))

    L.append("\n## 8. Analysis choices where the pre-registration is silent (conservative option)\n")
    L += [f"- {c}" for c in CHOICES]
    L.append("- Quota refusals (HTTP 403 'exceeds your available quota') are missing data, never "
             "'rejects'. Superseded runs are listed in `results/superseded.json`.")
    L.append("\n## 9. Lineup changes after the lock\n")
    for m, why in DROPPED.items():
        L.append(f"- {_short(m)}: {why}. Decided 2026-10-10 after the lock, before any main-run data for "
                 f"this model existed. Kaggle reserves input cost + 128K x output price per call "
                 f"(about $1.28 for claude-sonnet-5), so 8 parallel calls (about $10.24) exceed the $10 "
                 f"daily quota; fixing it would require editing locked task files and re-pushing.")
    Path(path).write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")


# ---------------------------------------------------------------- main

def run(results_dir: Path, out_csv: Path, out_md: Path, fig_dir: Path, superseded_path: Path,
        items_path: Path | None = None, hash_path: Path | None = None, reps: int = N_BOOT) -> dict:
    _setup()
    superseded = load_superseded(superseded_path)
    files = glob.glob(str(results_dir / "**" / "*.run.json"), recursive=True)
    df = load_calls(results_dir, superseded)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    df.drop(columns=["raw"], errors="ignore").to_csv(out_csv, index=False)

    hash_ok = "n/a"
    if items_path and hash_path and items_path.exists() and hash_path.exists():
        hash_ok = hashlib.sha256(items_path.read_bytes()).hexdigest() == hash_path.read_text().split()[0]

    live = df[~df["superseded"]].copy()
    comp = completeness(df)
    acc = accuracy_table(live, reps=reps)
    tests = delta_tests(live, comp, reps=reps)
    dial = dial_labels(live, comp)
    cost = cost_table(live)
    noise = noise_table(live)
    explore = explore_tokens(live)

    reps_used = sorted(live["repeat"].unique().tolist())
    R = len(reps_used)
    pending = [f"{_short(r.model)} ({r.status})" for r in comp.itertuples() if r.status != "complete"]
    n_text = (f"n per point: 20 items × {R} repeats = up to {20 * R} calls "
              f"per model × family × level (exact n in results/summary.md). Excluded: "
              f"{len(superseded)} superseded runs; quota refusals are missing data. "
              f"Not shown: {', '.join(pending) or 'none'}.")
    n_lineup = len([m for m in LINEUP if m not in DROPPED])
    waiting = [_short(r.model) for r in comp.itertuples()
               if r.status != "complete" and r.model not in DROPPED]
    tail = f" ({', '.join(waiting)} pending)" if waiting else ""

    def short(n_point: str) -> str:
        return f"{n_point} · {n_lineup} models{tail}, 20 questions × {R} repeats per level"

    per_level = short(f"n = {20 * R} answers per point")
    pooled = short(f"n = {60 * R} answers per point")
    fig_cost_vs_gain(tests, cost, fig_dir, n_text, short("n = 20 questions per point (paired)"))
    fig_cover(tests, cost, fig_dir)
    fig_dial_curves(acc, fig_dir, n_text, per_level)
    fig_token_ladder(dial, fig_dir, n_text, pooled)
    fig_token_ladder_by_family(explore, fig_dir, n_text, per_level)
    fig_cost_per_correct(cost, fig_dir, n_text, per_level)
    fig_forest(tests, fig_dir, n_text, short("n = 20 questions per row (paired)"))
    fig_format(acc, fig_dir, n_text, short(f"n = {60 * R} answers per cell"))
    write_summary(out_md, n_files=len(files), superseded=superseded, hash_ok=hash_ok, comp=comp,
                  acc=acc, tests=tests, dial=dial, cost=cost, noise=noise, explore=explore)
    return {"calls": df, "acc": acc, "tests": tests, "dial": dial, "cost": cost, "noise": noise,
            "comp": comp, "explore": explore}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", default=str(ROOT / "results" / "main"))
    ap.add_argument("--out-dir", default=str(ROOT / "results"))
    ap.add_argument("--fig-dir", default=str(ROOT / "analysis" / "figures"))
    ap.add_argument("--reps", type=int, default=N_BOOT)
    a = ap.parse_args()
    out = Path(a.out_dir)
    run(Path(a.results), out / "calls.csv", out / "summary.md", Path(a.fig_dir),
        ROOT / "results" / "superseded.json", ROOT / "data" / "test_items.json",
        ROOT / "data" / "test_items.sha256", reps=a.reps)
    print(f"wrote {out / 'calls.csv'}, {out / 'summary.md'}, figures in {a.fig_dir}")


if __name__ == "__main__":
    main()
