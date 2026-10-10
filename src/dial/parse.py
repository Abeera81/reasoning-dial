"""Answer parser (Tech Design §4). Pure stdlib; inlined into each Kaggle task file.

Outcomes: "correct", "wrong", "format_fail" (strict extraction unparseable).
"api_error" is assigned by the caller when the model call itself raised.
"""

import re

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_THINK_OPEN = re.compile(r"<think>", re.IGNORECASE)
_THINK_CLOSE = re.compile(r"</think>", re.IGNORECASE)
_MARKER = re.compile(
    r"FINAL[ \t]+ANSWER[ \t]*[*_`]*[ \t]*[:：][ \t]*(.*)$",
    re.IGNORECASE | re.MULTILINE,
)
_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")
_INT = re.compile(r"-?\d+")


def strip_think(raw: str) -> str:
    """Remove <think> blocks. An unclosed <think> runs to the end of the text;
    a stray </think> with no opener removes everything before it."""
    text = _THINK_BLOCK.sub("", raw)
    m = _THINK_OPEN.search(text)
    if m:
        text = text[: m.start()]
    closes = list(_THINK_CLOSE.finditer(text))
    if closes:
        text = text[closes[-1].end():]
    return text


def _clean(s: str) -> str:
    s = s.strip()
    s = re.sub(r"[*_`]", "", s)
    s = s.strip().strip("\"'“”‘’").strip()
    s = s.rstrip(".,!").strip()
    return s


def normalize(s: str, answer_type: str, known_names: list[str]):
    """Return the normalized answer (int or canonical name), or None if unparseable."""
    if s is None:
        return None
    s = _clean(s)
    if answer_type == "int":
        m = _INT.search(_THOUSANDS.sub("", s))
        return int(m.group()) if m else None
    if answer_type == "name":
        found = {
            n for n in known_names
            if re.search(rf"(?<![A-Za-z]){re.escape(n)}(?![A-Za-z])", s, re.IGNORECASE)
        }
        return found.pop() if len(found) == 1 else None
    raise ValueError(f"unknown answer_type {answer_type!r}")


def parse(raw: str, answer_type: str, known_names: list[str]) -> dict:
    """Strict extraction from the last FINAL ANSWER line; lenient fallback on the
    last non-empty visible line (secondary accuracy only)."""
    visible = strip_think(raw or "")
    markers = list(_MARKER.finditer(visible))
    parsed = normalize(markers[-1].group(1), answer_type, known_names) if markers else None
    lenient = parsed
    if lenient is None:
        lines = [ln for ln in visible.splitlines() if ln.strip()]
        if lines:
            lenient = normalize(lines[-1], answer_type, known_names)
    return {
        "parsed": parsed,
        "lenient_parsed": lenient,
        "outcome_hint": "ok" if parsed is not None else "format_fail",
    }


def grade(parsed, expected, answer_type: str) -> bool:
    if parsed is None:
        return False
    if answer_type == "int":
        return parsed == int(expected)
    return str(parsed).lower() == str(expected).lower()


def outcome(parsed, expected, answer_type: str) -> str:
    if parsed is None:
        return "format_fail"
    return "correct" if grade(parsed, expected, answer_type) else "wrong"
