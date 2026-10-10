import pytest

from dial.parse import grade, normalize, outcome, parse, strip_think

NAMES = ["Ana", "Ben", "Cleo", "Dev", "Eli", "Fay", "Gus", "Hana"]


def p_int(raw):
    return parse(raw, "int", NAMES)


def p_name(raw):
    return parse(raw, "name", NAMES)


@pytest.mark.parametrize("raw, want", [
    ("Work...\nFINAL ANSWER: 42", 42),
    ("**FINAL ANSWER:** 42", 42),
    ("**FINAL ANSWER**: 42", 42),
    ("Final Answer: `42`", 42),
    ("final answer：42", 42),
    ("FINAL ANSWER: 1,234.", 1234),
    ("FINAL ANSWER: $12,345", 12345),
    ("FINAL ANSWER: 1,234,567", 1234567),
    ("FINAL ANSWER: -7", -7),
    ("FINAL ANSWER: \"135\"", 135),
    ("FINAL ANSWER: 135 litres", 135),
    ("FINAL ANSWER: 3\nFINAL ANSWER: 4", 4),           # last marker wins
    ("FINAL ANSWER: 3 \n\nSome trailing text", 3),
])
def test_int_strict(raw, want):
    r = p_int(raw)
    assert r["parsed"] == want and r["outcome_hint"] == "ok"


def test_think_block_removed():
    raw = "<think>FINAL ANSWER: 9</think>\n\nFINAL ANSWER: 5"
    assert p_int(raw)["parsed"] == 5


def test_think_only_marker_is_ignored():
    raw = "<think>maybe FINAL ANSWER: 9</think>\nThe answer is 5."
    r = p_int(raw)
    assert r["parsed"] is None and r["outcome_hint"] == "format_fail"
    assert r["lenient_parsed"] == 5


def test_unclosed_think_runs_to_end():
    raw = "FINAL ANSWER: 5\n<think>reconsider... FINAL ANSWER: 9"
    assert p_int(raw)["parsed"] == 5
    assert p_int("<think>never closed FINAL ANSWER: 9")["parsed"] is None


def test_stray_close_tag():
    assert strip_think("reasoning FINAL ANSWER: 9</think>\nFINAL ANSWER: 5").strip() == "FINAL ANSWER: 5"


def test_case_insensitive_think():
    assert p_int("<THINK>x FINAL ANSWER: 1</Think>FINAL ANSWER: 2")["parsed"] == 2


def test_missing_marker_format_fail_lenient_last_line():
    r = p_int("I think it is\n\n270\n")
    assert r["parsed"] is None and r["outcome_hint"] == "format_fail"
    assert r["lenient_parsed"] == 270


def test_marker_without_value_is_format_fail():
    r = p_int("FINAL ANSWER:\n42")
    assert r["parsed"] is None
    assert r["lenient_parsed"] == 42


def test_empty_and_none():
    assert p_int("")["parsed"] is None
    assert p_int(None)["lenient_parsed"] is None


@pytest.mark.parametrize("raw, want", [
    ("FINAL ANSWER: Cleo", "Cleo"),
    ("FINAL ANSWER: **cleo**", "Cleo"),
    ("FINAL ANSWER: Cleo.", "Cleo"),
    ("FINAL ANSWER: It is Cleo", "Cleo"),
    ("FINAL ANSWER: Cleo or Ana", None),        # two names -> unparseable
    ("FINAL ANSWER: Cleopatra", None),          # whole-word match only
    ("FINAL ANSWER: nobody", None),
])
def test_name(raw, want):
    assert p_name(raw)["parsed"] == want


def test_grade_and_outcome():
    assert grade(1234, "1234", "int")
    assert not grade(1235, "1234", "int")
    assert grade("Cleo", "cleo", "name")
    assert outcome(None, "5", "int") == "format_fail"
    assert outcome(5, "5", "int") == "correct"
    assert outcome(6, "5", "int") == "wrong"


def test_normalize_rejects_unknown_type():
    with pytest.raises(ValueError):
        normalize("1", "float", NAMES)
