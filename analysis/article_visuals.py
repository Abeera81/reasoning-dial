"""Two explanatory visuals for the DEV article (not analysis results).

- anatomy_overcount.png: real gpt-5.4-mini Distract replies, with every number checked
  against the raw run files and the locked items before drawing.
- pipeline.png: how an item travels from the seeded generator to a number in the article.

Run: python analysis/article_visuals.py   (writes to analysis/figures/article/)
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis" / "figures" / "article"
MINI = "#CC79A7"
OWNED = "#009E73"
DISTRACTOR = "#D55E00"
INK = "#1a1a1a"


def _items():
    data = json.loads((ROOT / "data" / "test_items.json").read_text(encoding="utf-8"))
    items = data["items"] if isinstance(data, dict) else data
    return {it["id"]: it for it in items}


def _mini_records():
    recs = []
    for f in glob.glob(str(ROOT / "results/main/dial-*/1/gpt-5.4-mini-2026-03-17/46317*/*.run.json")):
        run = json.loads(Path(f).read_text(encoding="utf-8"))
        for s in run.get("subruns", []):
            try:
                recs.append(s["results"][0]["dictResult"])
            except (KeyError, IndexError, TypeError):
                continue
    return recs


def _find(recs, item_id, level, parsed):
    hits = [r for r in recs if r["item_id"] == item_id and r["level"] == level and r["parsed"] == str(parsed)]
    assert hits, f"no {item_id}/{level} reply with parsed={parsed} in the run files"
    return hits[0]


def anatomy():
    items, recs = _items(), _mini_records()
    p16 = items["distract-016"]["prompt"]
    p12 = items["distract-012"]["prompt"]
    p11 = items["distract-011"]["prompt"]
    # distract-016: owned 2; 8,377 sold; code prints 3*3 = 9; homework 44*37 = 1,628
    assert "8,377" in p16 and "44 crates each hold 37" in p16 and 'len(stock) * 3' in p16
    assert 2 + 8377 + 9 + 44 * 37 == 10016
    # distract-012: owned 5; homework 27*24 = 648; code prints 1*6 = 6; 1,590 sold
    assert "27 crates each hold 24" in p12 and "len(stock) * 6" in p12 and "1,590" in p12
    assert 5 + 27 * 24 + 6 + 1590 == 2249
    # distract-011: the homework problem itself, 22*29 = 638
    assert "22 crates each hold 29" in p11 and 22 * 29 == 638
    r16 = _find(recs, "distract-016", "high", 10016)
    r12 = _find(recs, "distract-012", "high", 2249)
    r11 = _find(recs, "distract-011", "high", 638)
    for it_id, r in (("distract-016", r16), ("distract-012", r12), ("distract-011", r11)):
        assert r["expected"] == str(items[it_id]["answer"])

    rows = [
        ("distract-016", "You have a chisel and a drill.", "tools", int(items["distract-016"]["answer"]), r16,
         [("2", OWNED, "owned"), ("8,377", DISTRACTOR, "shop sales"),
          ("9", DISTRACTOR, "code output"), ("1,628", DISTRACTOR, "homework (44 × 37)")],
         "it added every number in the prompt"),
        ("distract-012", "You have a drum, a cello, a flute, a trumpet and a violin.", "musical instruments",
         int(items["distract-012"]["answer"]), r12,
         [("5", OWNED, "owned"), ("648", DISTRACTOR, "homework (27 × 24)"),
          ("6", DISTRACTOR, "code output"), ("1,590", DISTRACTOR, "a shop's sales")],
         "same move, different item"),
        ("distract-011", "You have a poetry collection and a biography.", "books",
         int(items["distract-011"]["answer"]), r11,
         [("638", DISTRACTOR, "a classmate's homework (22 × 29)")],
         "it solved someone else's problem instead"),
    ]

    fig = plt.figure(figsize=(16, 8.4), dpi=100, facecolor="white")
    fig.text(0.03, 0.94, "Counting to two, at reasoning effort ‘high’", fontsize=24, fontweight="bold", color=INK)
    fig.text(0.03, 0.895, "Real gpt-5.4-mini replies from the main run. Every wrong Distract answer, from every model, "
             "was an over-count.", fontsize=14, color="#444444")
    y0 = 0.80
    for i, (iid, first, cat, truth, rec, parts, gloss) in enumerate(rows):
        y = y0 - i * 0.255
        box = FancyBboxPatch((0.03, y - 0.205), 0.94, 0.215, boxstyle="round,pad=0.004,rounding_size=0.012",
                             transform=fig.transFigure, fc="#fafafa", ec="#dddddd", lw=1.2)
        fig.patches.append(box)
        fig.text(0.05, y - 0.03, f"{iid}", fontsize=12, color="#777777", family="monospace")
        fig.text(0.05, y - 0.075, first, fontsize=15, color=INK)
        fig.text(0.05, y - 0.12, f"Question: Calculate how many {cat} you have.", fontsize=15, color=INK)
        fig.text(0.05, y - 0.175, f"Correct answer: {truth}", fontsize=15, color=OWNED, fontweight="bold")
        # the model's sum
        x = 0.50
        fig.text(x, y - 0.03, f"gpt-5.4-mini · high · {int(rec['output_tokens']):,} output tokens",
                 fontsize=12, color=MINI, fontweight="bold")
        xx = x
        for j, (num, col, _) in enumerate(parts):
            if j:
                t = fig.text(xx, y - 0.095, " + ", fontsize=22, color="#555555", va="center")
                xx += 0.03
            t = fig.text(xx, y - 0.095, num, fontsize=22, color=col, fontweight="bold", va="center")
            xx += 0.0125 * len(num) + 0.012
        if len(parts) > 1:
            fig.text(xx, y - 0.095, f" = {int(rec['parsed']):,}", fontsize=22, color=INK, fontweight="bold",
                     va="center")
        legend = " · ".join(f"{n} = {lbl}" for n, _, lbl in parts)
        fig.text(x, y - 0.15, legend, fontsize=12, color="#555555")
        fig.text(x, y - 0.185, f"FINAL ANSWER: {rec['parsed']}   ← {gloss}", fontsize=12.5, color=INK,
                 family="monospace")
    fig.text(0.03, 0.015, "Source: results/main run files (gpt-5.4-mini-2026-03-17, Kaggle run 4631776); prompts from "
             "data/test_items.json (locked, SHA-256 90dd5498…0042). Sums verified in analysis/article_visuals.py.",
             fontsize=10.5, color="#666666")
    fig.savefig(OUT / "anatomy_overcount.png", facecolor="white")
    plt.close(fig)


def pipeline():
    steps = [
        ("generate.py", "seeded generators\nanswers computed by code,\nlogic puzzles brute-force\nchecked for one solution", "#E8F4FA"),
        ("test_items.json", "60 items, SHA-256\nlocked + pre-registered\nbefore any main run", "#FFF4E0"),
        ("build_tasks.py", "inlines items + parser\ninto 4 task files that\ndiffer only in the level", "#E8F4FA"),
        ("Kaggle Benchmarks", "4 tasks: none, low,\nmedium, high\nreasoning=<level>\n8 calls in parallel", "#EAF6EF"),
        ("parse.py", "last ‘FINAL ANSWER:’ line\ndeterministic grading\nno LLM judge", "#E8F4FA"),
        ("analyze.py", "paired bootstrap + Wilcoxon\nHolm across 12 tests\nsummary.md + figures", "#F5EAF1"),
    ]
    fig = plt.figure(figsize=(16, 4.6), dpi=100, facecolor="white")
    fig.text(0.5, 0.92, "One item’s path: from a seed to a number in this post", ha="center", fontsize=20,
             fontweight="bold", color=INK)
    n = len(steps)
    w, gap = 0.142, (0.96 - 6 * 0.142) / 5
    for i, (title, body, fc) in enumerate(steps):
        x = 0.02 + i * (w + gap)
        fig.patches.append(FancyBboxPatch((x, 0.16), w, 0.58, boxstyle="round,pad=0.004,rounding_size=0.02",
                                          transform=fig.transFigure, fc=fc, ec="#999999", lw=1.2))
        fig.text(x + w / 2, 0.64, title, ha="center", va="center", fontsize=14, fontweight="bold", color=INK,
                 family="monospace" if title.endswith((".py", ".json")) else None)
        fig.text(x + w / 2, 0.40, body, ha="center", va="center", fontsize=11.5, color="#333333", linespacing=1.4)
        if i < n - 1:
            fig.patches.append(FancyArrowPatch((x + w + 0.003, 0.45), (x + w + gap - 0.003, 0.45),
                                               transform=fig.transFigure, arrowstyle="-|>", mutation_scale=18,
                                               color="#555555", lw=1.6))
    fig.text(0.5, 0.05, "Same 60 items, same prompt, same parser at every level. The only thing that changes "
             "between the four Kaggle tasks is the reasoning-effort value.", ha="center", fontsize=12.5,
             color="#444444")
    fig.savefig(OUT / "pipeline.png", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    anatomy()
    pipeline()
    print("wrote", OUT / "anatomy_overcount.png", OUT / "pipeline.png")
