"""Seeded item generators for the three task families (Tech Design §3).

Every answer is computed by code. Each family draws from its own
``random.Random`` seeded from ``(family, seed)``; the global ``random``
module is never used.
"""

import itertools
import json
import random
import sys
from pathlib import Path

FAMILIES = ["deduce", "arith", "distract"]
NAMES = ["Ana", "Ben", "Cleo", "Dev", "Eli", "Fay", "Gus", "Hana"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

ANSWER_INSTRUCTION = {
    "name": "Answer with the person's name.",
    "int": "Answer with a whole number.",
}


def with_suffix(body: str, answer_type: str) -> str:
    """Append the shared answer suffix (§3.4), identical at every level."""
    return (
        f"{body}\n\n"
        f"Answer instruction: {ANSWER_INSTRUCTION[answer_type]}\n\n"
        "End your response with a final line in exactly this format:\n"
        "FINAL ANSWER: <answer>"
    )


# ---------------------------------------------------------------- deduce

N_PEOPLE = 5
NUMBER_WORDS = {5: "Five", 6: "Six", 7: "Seven"}


def _clue_holds(clue, pos) -> bool:
    kind, a, b = clue
    if kind == "not_on":
        return pos[a] != b
    if kind == "on":
        return pos[a] == b
    if kind == "before":
        return pos[a] < pos[b]
    if kind == "immediately_before":
        return pos[a] + 1 == pos[b]
    if kind == "not_adjacent":
        return abs(pos[a] - pos[b]) != 1
    raise ValueError(kind)


def _count_solutions(people, clues, limit=2) -> int:
    n = 0
    for perm in itertools.permutations(range(len(people))):
        pos = dict(zip(people, perm))
        if all(_clue_holds(c, pos) for c in clues):
            n += 1
            if n >= limit:
                break
    return n


def _render_clue(clue, days) -> str:
    kind, a, b = clue
    if kind == "not_on":
        return f"{a} does not give the talk on {days[b]}."
    if kind == "on":
        return f"{a} gives the talk on {days[b]}."
    if kind == "before":
        return f"{a} gives the talk on an earlier day than {b}."
    if kind == "immediately_before":
        return f"{a} gives the talk on the day immediately before {b}."
    if kind == "not_adjacent":
        return f"{a} and {b} do not give their talks on consecutive days."
    raise ValueError(kind)


def _deduce_item(rng: random.Random, idx: int, n: int = N_PEOPLE) -> dict:
    people = sorted(rng.sample(NAMES, n), key=NAMES.index)
    days = DAYS[:n]
    order = people[:]
    rng.shuffle(order)
    pos = {p: i for i, p in enumerate(order)}  # truth: person -> day index

    cands = []
    for p in people:
        cands.append(("on", p, pos[p]))
        cands += [("not_on", p, d) for d in range(n) if d != pos[p]]
    for a, b in itertools.permutations(people, 2):
        if pos[a] < pos[b]:
            cands.append(("before", a, b))
            if pos[a] + 1 == pos[b]:
                cands.append(("immediately_before", a, b))
        if pos[a] < pos[b] - 1:
            cands.append(("not_adjacent", a, b))
    rng.shuffle(cands)

    clues = []
    for c in cands:
        if c[0] == "on" and any(x[0] == "on" for x in clues):
            continue  # at most one on() clue
        clues.append(c)
        if _count_solutions(people, clues) == 1:
            break
    # Greedy pruning: drop any clue whose removal keeps the solution unique.
    for c in list(clues):
        trial = [x for x in clues if x is not c]
        if _count_solutions(people, trial) == 1:
            clues = trial
    assert _count_solutions(people, clues) == 1

    pinned = {c[1] for c in clues if c[0] == "on"}
    q_day = rng.choice([d for d in range(n) if order[d] not in pinned])
    answer = order[q_day]

    listed = ", ".join(people[:-1]) + f" and {people[-1]}"
    lines = "\n".join(f"{i + 1}. {_render_clue(c, days)}" for i, c in enumerate(clues))
    body = (
        f"{NUMBER_WORDS[n]} people, {listed}, each give exactly one talk. The talks are "
        f"on {n} consecutive days, {days[0]} to {days[-1]}, one talk per day.\n\n"
        f"Clues:\n{lines}\n\n"
        f"Question: Who gives the talk on {days[q_day]}?"
    )
    counts = {}
    for c in clues:
        counts[c[0]] = counts.get(c[0], 0) + 1
    return {
        "id": f"deduce-{idx:03d}",
        "family": "deduce",
        "answer_type": "name",
        "prompt": with_suffix(body, "name"),
        "answer": answer,
        "meta": {
            "n_people": n,
            "n_clues": len(clues),
            "clue_types": counts,
            "people": people,
            "question_day": days[q_day],
        },
    }


# ---------------------------------------------------------------- arith


def _arith_warehouse(rng):
    t, b, s = rng.randint(3, 9), rng.randint(12, 48), rng.randint(3, 8)
    q = rng.randint((t * b) // s + 30, (t * b) // s + 200)
    a = s * q - t * b
    k = rng.randint(5, q - 20)
    steps = [t * b, a + t * b, (a + t * b) // s, q - k, s * (q - k)]
    text = (
        f"A warehouse holds {a} boxes. A truck then delivers {t} loads of {b} boxes "
        f"each. All the boxes in the warehouse are then split equally among {s} stores, "
        f"and each store sells {k} of the boxes it received. How many unsold boxes do "
        f"the {s} stores have in total?"
    )
    return text, {"a": a, "t": t, "b": b, "s": s, "k": k}, steps


def _arith_trip(rng):
    h1, h2 = rng.randint(2, 5), rng.randint(2, 5)
    v1, v2 = rng.randrange(40, 95, 5), rng.randrange(40, 95, 5)
    d, p = rng.randint(11, 79), rng.randint(2, 9)
    steps = [h1 * v1, h2 * v2, h1 * v1 + h2 * v2, h1 * v1 + h2 * v2 + d,
             (h1 * v1 + h2 * v2 + d) * p]
    text = (
        f"A courier drives for {h1} hours at {v1} km/h, then for {h2} hours at "
        f"{v2} km/h. A road closure adds a detour of {d} km to the trip. The courier "
        f"is paid {p} dollars for every kilometre driven. How many dollars is the "
        f"courier paid for the whole trip?"
    )
    return text, {"h1": h1, "v1": v1, "h2": h2, "v2": v2, "d": d, "p": p}, steps


def _arith_savings(rng):
    w, n = rng.randrange(120, 400, 20), rng.randint(6, 20)
    pct = rng.randrange(15, 60, 5)
    total = w * n
    rent = total * pct // 100
    m, c = rng.randint(2, 9), rng.randint(12, 45)
    steps = [total, rent, total - rent, m * c, total - rent - m * c]
    text = (
        f"Maya earns {w} dollars per week for {n} weeks. She spends {pct}% of her "
        f"total earnings on rent. Then she buys {m} books at {c} dollars each. How "
        f"many dollars does Maya have left?"
    )
    return text, {"w": w, "n": n, "pct": pct, "m": m, "c": c}, steps


def _arith_recipe(rng):
    s, k = rng.randint(2, 6), rng.randint(3, 12)
    g, w, m = rng.randrange(150, 600, 10), rng.randint(15, 90), rng.randint(3, 9)
    big = s * k
    steps = [big // s, g * k, g * k + w, m * (g * k + w)]
    text = (
        f"A recipe for {s} servings uses {g} grams of flour. A bakery makes {m} "
        f"batches, and each batch is {big} servings. On top of the recipe amount, "
        f"{w} grams of flour are spilled during each batch. How many grams of flour "
        f"does the bakery use in total?"
    )
    return text, {"s": s, "big": big, "g": g, "w": w, "m": m}, steps


ARITH_TEMPLATES = {
    "warehouse": _arith_warehouse,
    "trip": _arith_trip,
    "savings": _arith_savings,
    "recipe": _arith_recipe,
}


def _arith_item(rng: random.Random, idx: int) -> dict:
    tid = list(ARITH_TEMPLATES)[idx % len(ARITH_TEMPLATES)]
    while True:
        text, params, steps = ARITH_TEMPLATES[tid](rng)
        if all(x > 0 for x in steps) and 100 <= steps[-1] <= 99999:
            break
    return {
        "id": f"arith-{idx:03d}",
        "family": "arith",
        "answer_type": "int",
        "prompt": with_suffix(text, "int"),
        "answer": str(steps[-1]),
        "meta": {"template": tid, "steps": len(steps), "params": params},
    }


# ---------------------------------------------------------------- distract

CATEGORIES = {
    "fruits": [("an apple", "apples"), ("a pear", "pears"), ("a plum", "plums"),
               ("an orange", "oranges"), ("a peach", "peaches"), ("a mango", "mangoes"),
               ("a lemon", "lemons"), ("a banana", "bananas")],
    "tools": [("a hammer", "hammers"), ("a saw", "saws"), ("a drill", "drills"),
              ("a wrench", "wrenches"), ("a screwdriver", "screwdrivers"),
              ("a chisel", "chisels"), ("a level", "levels")],
    "musical instruments": [("a guitar", "guitars"), ("a violin", "violins"),
                            ("a flute", "flutes"), ("a drum", "drums"),
                            ("a trumpet", "trumpets"), ("a cello", "cellos")],
    "books": [("a novel", "novels"), ("a cookbook", "cookbooks"), ("an atlas", "atlases"),
              ("a dictionary", "dictionaries"), ("a biography", "biographies"),
              ("a poetry collection", "poetry collections")],
}
FORBIDDEN_PHRASES = ["you have", "you own", "you also", "you get", "gives you",
                     "you buy", "you receive", "you lose", "you eat"]
PLACES = ["Spain", "Chile", "Italy", "Japan", "Kenya", "Peru", "Norway", "Egypt"]
TOWNS = ["Larkhill", "Brookfield", "Easton", "Millbrook", "Ashford", "Kingsley"]
PEOPLE = ["Your neighbour", "Your cousin", "A classmate", "A colleague"]


def _bare(noun_with_article: str) -> str:
    return noun_with_article.split(" ", 1)[1]


def _distractor(kind, rng, owned, others) -> str:
    if kind == "probability":
        obj = _bare(rng.choice(owned)[0])
        return (f"There is a {rng.randint(11, 89)}% chance that the {obj} comes "
                f"from {rng.choice(PLACES)}.")
    if kind == "fact":
        plural = rng.choice(others)[1]
        return (f"A shop in {rng.choice(TOWNS)} sold {rng.randint(1200, 9800):,} "
                f"{plural} last {rng.choice(['week', 'month', 'year'])}.")
    if kind == "math":
        a, b = rng.randint(12, 49), rng.randint(13, 37)
        return (f"{rng.choice(PEOPLE)} is working on a homework problem: if {a} crates "
                f"each hold {b} {rng.choice(others)[1]}, how many are there altogether?")
    if kind == "code":
        names = [_bare(x[0]) for x in rng.sample(others, min(3, len(others)))]
        listed = ", ".join(f'"{x}"' for x in names)
        return (f"A friend shows you this code:\n"
                f"```python\nstock = [{listed}]\nprint(len(stock) * {rng.randint(3, 12)})\n```")
    raise ValueError(kind)


DISTRACTOR_KINDS = ["probability", "fact", "math", "code"]


def _distract_item(rng: random.Random, idx: int) -> dict:
    category = rng.choice(sorted(CATEGORIES))
    k = rng.choice([2, 3, 4, 5])
    pool = CATEGORIES[category]
    owned = rng.sample(pool, k)
    others = [x for x in pool if x not in owned]
    names = [x[0] for x in owned]
    first = f"You have {', '.join(names[:-1])} and {names[-1]}."
    kinds = rng.sample(DISTRACTOR_KINDS, rng.randint(1, 3))
    distractors = [_distractor(kd, rng, owned, others) for kd in kinds]
    question = f"Question: Calculate how many {category} you have."
    middle = "\n\n".join(distractors)
    low = middle.lower()
    assert not any(p in low for p in FORBIDDEN_PHRASES), middle
    body = f"{first}\n\n{middle}\n\n{question}"
    return {
        "id": f"distract-{idx:03d}",
        "family": "distract",
        "answer_type": "int",
        "prompt": with_suffix(body, "int"),
        "answer": str(k),
        "meta": {"k": k, "category": category, "distractor_types": kinds,
                 "distractor_chars": len(middle)},
    }


# ---------------------------------------------------------------- entry points

_MAKERS = {"deduce": _deduce_item, "arith": _arith_item, "distract": _distract_item}


def generate(family: str, n: int, seed: int) -> list[dict]:
    rng = random.Random(f"{family}:{seed}")
    return [_MAKERS[family](rng, i) for i in range(n)]


def generate_all(n_per_family: int, seed: int) -> list[dict]:
    return [item for fam in FAMILIES for item in generate(fam, n_per_family, seed)]


def write_items(path: str | Path, n_per_family: int, seed: int) -> list[dict]:
    items = generate_all(n_per_family, seed)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(items, indent=1, ensure_ascii=False) + "\n",
                          encoding="utf-8", newline="\n")
    return items


if __name__ == "__main__":
    # python -m dial.generate <out.json> <n_per_family> <seed>
    out, n, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    print(f"wrote {len(write_items(out, n, seed))} items to {out}")
