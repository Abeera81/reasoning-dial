"""Generator checks. Deduce and Arith answers are re-derived here from the prompt
text alone, without using the generator's internal clue/step data."""

import itertools
import json
import re
from pathlib import Path

import pytest

from dial import generate as g

ROOT = Path(__file__).resolve().parents[1]
SUFFIX_RE = re.compile(
    r"\n\nAnswer instruction: (Answer with the person's name\.|Answer with a whole number\.)"
    r"\n\nEnd your response with a final line in exactly this format:\nFINAL ANSWER: <answer>\Z"
)
SEEDS = [1002, 2026, 7]


@pytest.fixture(scope="module", params=SEEDS)
def items(request):
    return g.generate_all(20, request.param)


def body(item):
    return SUFFIX_RE.split(item["prompt"])[0]


def test_same_seed_same_output():
    assert g.generate_all(4, 1002) == g.generate_all(4, 1002)
    assert g.generate_all(4, 1002) != g.generate_all(4, 2026)


def test_shape_and_suffix(items):
    assert [i["family"] for i in items] == ["deduce"] * 20 + ["arith"] * 20 + ["distract"] * 20
    assert len({i["id"] for i in items}) == len(items)
    assert len({i["prompt"] for i in items}) == len(items)
    for it in items:
        m = SUFFIX_RE.search(it["prompt"])
        assert m, it["id"]
        want = "Answer with the person's name." if it["answer_type"] == "name" else "Answer with a whole number."
        assert m.group(1) == want
        assert "FINAL ANSWER" not in body(it)


# ---------------------------------------------------------------- deduce: independent brute force

CLUE_PATTERNS = [
    (re.compile(r"^(\w+) does not give the talk on (\w+)\.$"), lambda a, d: lambda p, D: p[a] != D[d]),
    (re.compile(r"^(\w+) gives the talk on an earlier day than (\w+)\.$"), lambda a, b: lambda p, D: p[a] < p[b]),
    (re.compile(r"^(\w+) gives the talk on the day immediately before (\w+)\.$"), lambda a, b: lambda p, D: p[b] - p[a] == 1),
    (re.compile(r"^(\w+) and (\w+) do not give their talks on consecutive days\.$"), lambda a, b: lambda p, D: abs(p[a] - p[b]) != 1),
    (re.compile(r"^(\w+) gives the talk on (\w+)\.$"), lambda a, d: lambda p, D: p[a] == D[d]),
]


def solve_deduce(text):
    people_line = re.search(r"people, (.+?), each give exactly one talk", text).group(1)
    people = re.split(r", | and ", people_line)
    first, last = re.search(r"days, (\w+) to (\w+), one talk per day", text).groups()
    week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    days = week[week.index(first): week.index(last) + 1]
    D = {d: i for i, d in enumerate(days)}
    checks = []
    for line in re.findall(r"^\d+\. (.+)$", text, re.MULTILINE):
        for pat, make in CLUE_PATTERNS:
            m = pat.match(line)
            if m:
                checks.append(make(*m.groups()))
                break
        else:
            raise AssertionError(f"unparsed clue: {line}")
    q_day = re.search(r"Who gives the talk on (\w+)\?", text).group(1)
    sols = []
    for perm in itertools.permutations(range(len(people))):
        p = dict(zip(people, perm))
        if all(c(p, D) for c in checks):
            sols.append(p)
    return people, sols, q_day, D, len(checks)


def test_deduce_unique_and_correct(items):
    for it in items:
        if it["family"] != "deduce":
            continue
        people, sols, q_day, D, n_clues = solve_deduce(body(it))
        assert len(people) == it["meta"]["n_people"]
        assert len(sols) == 1, it["id"]
        who = [x for x, d in sols[0].items() if d == D[q_day]]
        assert who == [it["answer"]], it["id"]
        assert n_clues == it["meta"]["n_clues"]
        # Retuned settings: 7 people Monday-Sunday, no on() clues, asked day Tue-Sat.
        assert len(people) == 7 and list(D) == ["Monday", "Tuesday", "Wednesday", "Thursday",
                                                "Friday", "Saturday", "Sunday"]
        assert not re.search(r"^\d+\. \w+ gives the talk on \w+day\.$", body(it), re.M)
        assert q_day in ("Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")


# ---------------------------------------------------------------- arith: independent recomputation

def nums(text):
    return [int(x) for x in re.findall(r"\d+", text)]


def exact_div(x, d):
    assert x % d == 0
    return x // d


def exact_pct(x, p):
    assert (x * p) % 100 == 0
    return x * p // 100


def solve_arith(text):
    """Recompute from the prompt numbers; return (answer, intermediates)."""
    if text.startswith("A warehouse"):
        a, t, b, s, pct, s2 = nums(text)
        assert s == s2
        total = a + t * b
        per = exact_div(total, s)
        left = per - exact_pct(per, pct)
        mids = [t * b, total, per, exact_pct(per, pct), left]
        return s * left, mids
    if text.startswith("A courier"):
        h, v, d2, k, c, pct = nums(text)
        km = h * v + d2
        litres = exact_div(km, k)
        cost = litres * c
        return cost + exact_pct(cost, pct), [h * v, km, litres, cost, exact_pct(cost, pct)]
    if text.startswith("Maya"):
        w, n, pct, m, c, j = nums(text)
        after = w * n - exact_pct(w * n, pct)
        left = after - m * c
        return exact_div(left, j), [w * n, exact_pct(w * n, pct), after, m * c, left]
    if text.startswith("A recipe"):
        s, g_, m, big, pct, stock = nums(text)
        batch = exact_div(g_, s) * big
        per_batch = batch + exact_pct(batch, pct)
        need = per_batch * m
        return need - stock, [exact_div(g_, s), batch, exact_pct(batch, pct), per_batch, need]
    raise AssertionError(text)


def test_arith_answers(items):
    templates = set()
    for it in items:
        if it["family"] != "arith":
            continue
        ans, mids = solve_arith(body(it))
        assert ans == int(it["answer"]), it["id"]
        assert 1000 <= ans <= 999999, it["id"]
        assert all(0 < x <= 99999 for x in mids), (it["id"], mids)
        assert it["meta"]["steps"] == 6 and len(mids) + 1 == 6
        assert "%" in it["meta"]["ops"] and "/" in it["meta"]["ops"]
        templates.add(it["meta"]["template"])
    assert len(templates) >= 4


# ---------------------------------------------------------------- distract

def test_distract_answers_and_blacklist(items):
    for it in items:
        if it["family"] != "distract":
            continue
        text = body(it)
        paras = text.split("\n\n")
        first, question = paras[0], paras[-1]
        assert first.startswith("You have ") and question.startswith("Question: Calculate how many")
        owned = re.split(r", | and ", first[len("You have "):-1])
        assert len(owned) == int(it["answer"]) == it["meta"]["k"]
        assert it["meta"]["category"] in question
        middle = "\n\n".join(paras[1:-1]).lower()
        assert middle, it["id"]
        for phrase in g.FORBIDDEN_PHRASES:
            assert phrase not in middle, (it["id"], phrase)


def test_calibration_file_matches_generator():
    # Calibration 1 (seed 1001) used the pre-retune generator and is kept as a record only.
    path = ROOT / "data" / "calibration_items_seed1002.json"
    if not path.exists():
        pytest.skip("calibration file not generated")
    want = g.generate("deduce", 8, 1002) + g.generate("arith", 8, 1002)
    assert json.loads(path.read_text(encoding="utf-8")) == want


def test_test_items_match_generator_and_hash():
    path = ROOT / "data" / "test_items.json"
    if not path.exists():
        pytest.skip("test items not generated yet")
    import hashlib
    assert json.loads(path.read_text(encoding="utf-8")) == g.generate_all(20, 2026)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert (ROOT / "data" / "test_items.sha256").read_text(encoding="utf-8").split()[0] == digest
