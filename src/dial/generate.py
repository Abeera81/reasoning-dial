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

# Retuned 2026-10-10 after calibration 1 (none-level accuracy ~100%):
# 7 people Monday-Sunday, no on() clues, question day Tuesday-Saturday.
N_PEOPLE = 7
ALLOW_ON_CLUE = False
QUESTION_DAYS = range(1, 6)  # Tuesday..Saturday
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
        if ALLOW_ON_CLUE:
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
    q_day = rng.choice([d for d in QUESTION_DAYS if d < n and order[d] not in pinned])
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
# Retuned 2026-10-10 after calibration 1: 6 operations per problem, each with at
# least one percentage step ("%") and one exact division ("/"); every intermediate
# is a positive integer of at most 5 digits; the final answer has 4-6 digits.
# A template returns (text, params, steps) with steps = [(op, value), ...], or None
# when a draw gives an inexact step (the caller redraws).


class _Inexact(Exception):
    pass


def _pct(x: int, p: int) -> int:
    if (x * p) % 100:
        raise _Inexact
    return x * p // 100


def _div(x: int, d: int) -> int:
    if x % d:
        raise _Inexact
    return x // d


def _arith_warehouse(rng):
    t, b, s = rng.randint(3, 9), rng.randint(12, 60), rng.randint(3, 9)
    pct = rng.randrange(10, 65, 5)
    base = (t * b) // s
    q = rng.randrange((base // 20 + 2) * 20, (base // 20 + 60) * 20, 20)
    a = s * q - t * b
    delivered = t * b
    total = a + delivered
    per_store = _div(total, s)
    sold = _pct(per_store, pct)
    left = per_store - sold
    steps = [("*", delivered), ("+", total), ("/", per_store), ("%", sold),
             ("-", left), ("*", s * left)]
    text = (
        f"A warehouse holds {a} boxes. A truck then delivers {t} loads of {b} boxes "
        f"each. All the boxes in the warehouse are then split equally among {s} stores. "
        f"Each store sells {pct}% of the boxes it received. How many unsold boxes do "
        f"the {s} stores have in total?"
    )
    return text, {"a": a, "t": t, "b": b, "s": s, "pct": pct}, steps


def _arith_fuel(rng):
    h, v, k = rng.randint(2, 6), rng.randrange(40, 100, 5), rng.randint(8, 16)
    c, pct = rng.randrange(180, 400, 20), rng.randrange(5, 30, 5)
    km1 = h * v
    d2 = rng.randint(20, 250)
    d2 += (-(km1 + d2)) % k  # total distance divisible by k
    total_km = km1 + d2
    litres = _div(total_km, k)
    cost = litres * c
    tax = _pct(cost, pct)
    steps = [("*", km1), ("+", total_km), ("/", litres), ("*", cost), ("%", tax),
             ("+", cost + tax)]
    text = (
        f"A courier drives for {h} hours at {v} km/h, then drives another {d2} km. "
        f"The van uses one litre of fuel for every {k} km. Fuel costs {c} rupees per "
        f"litre, and a fuel tax adds {pct}% to the fuel cost. How many rupees does the "
        f"fuel for the whole trip cost, including the tax?"
    )
    return text, {"h": h, "v": v, "d2": d2, "k": k, "c": c, "pct": pct}, steps


def _arith_savings(rng):
    w, n = rng.randrange(400, 1600, 20), rng.randint(8, 30)
    pct = rng.randrange(15, 50, 5)
    m, c, j = rng.randint(3, 12), rng.randint(25, 150), rng.randint(2, 6)
    total = w * n
    rent = _pct(total, pct)
    after = total - rent
    books = m * c
    left = after - books
    each = _div(left, j)
    steps = [("*", total), ("%", rent), ("-", after), ("*", books), ("-", left),
             ("/", each)]
    text = (
        f"Maya earns {w} dollars per week for {n} weeks. She spends {pct}% of her total "
        f"earnings on rent. Then she buys {m} books at {c} dollars each. She splits the "
        f"money she has left equally into {j} envelopes. How many dollars go into each "
        f"envelope?"
    )
    return text, {"w": w, "n": n, "pct": pct, "m": m, "c": c, "j": j}, steps


def _arith_recipe(rng):
    s = rng.randint(2, 6)
    g = s * rng.randint(40, 120)
    big, pct, m = rng.randrange(10, 60, 5), rng.randrange(5, 30, 5), rng.randint(3, 9)
    per_serving = _div(g, s)
    batch = per_serving * big
    spill = _pct(batch, pct)
    per_batch = batch + spill
    need = per_batch * m
    stock = rng.randint(500, max(600, need // 3))
    steps = [("/", per_serving), ("*", batch), ("%", spill), ("+", per_batch),
             ("*", need), ("-", need - stock)]
    text = (
        f"A recipe for {s} servings uses {g} grams of flour. A bakery makes {m} batches, "
        f"and each batch is {big} servings. In every batch an extra {pct}% of that "
        f"batch's recipe flour is lost to spills, so it has to be added on top. The "
        f"bakery already has {stock} grams of flour in stock. How many more grams of "
        f"flour does the bakery need to buy?"
    )
    return text, {"s": s, "g": g, "big": big, "pct": pct, "m": m, "stock": stock}, steps


ARITH_TEMPLATES = {
    "warehouse": _arith_warehouse,
    "fuel": _arith_fuel,
    "savings": _arith_savings,
    "recipe": _arith_recipe,
}


def _arith_ok(steps) -> bool:
    vals = [v for _, v in steps]
    ops = [op for op, _ in steps]
    return (
        len(steps) == 6 and "%" in ops and "/" in ops
        and all(isinstance(v, int) and v > 0 for v in vals)
        and all(v <= 99999 for v in vals[:-1])
        and 1000 <= vals[-1] <= 999999
    )


def _arith_item(rng: random.Random, idx: int) -> dict:
    tid = list(ARITH_TEMPLATES)[idx % len(ARITH_TEMPLATES)]
    while True:
        try:
            text, params, steps = ARITH_TEMPLATES[tid](rng)
        except _Inexact:
            continue
        if _arith_ok(steps):
            break
    return {
        "id": f"arith-{idx:03d}",
        "family": "arith",
        "answer_type": "int",
        "prompt": with_suffix(text, "int"),
        "answer": str(steps[-1][1]),
        "meta": {"template": tid, "steps": len(steps), "ops": [op for op, _ in steps],
                 "params": params},
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
