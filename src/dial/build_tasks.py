"""Write tasks/*.py from task_template.py.txt with items and parser inlined (Tech Design §5).

A Kaggle task is one pushed file, so everything it needs is inlined. The four
dial files differ only in the LEVELS line and the two @kbench.task(name=...) lines
(outer dial-<level>, inner dial-call-<level>); names must be string literals because `kaggle b t push` reads it with `ast`.

    PYTHONPATH=src python -m dial.build_tasks
"""

import json
import pprint
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(__file__).resolve().parent
TEMPLATE = SRC / "task_template.py.txt"
PARSER = SRC / "parse.py"
CALIBRATION_ITEMS = ROOT / "data" / "calibration_items.json"
TEST_ITEMS = ROOT / "data" / "test_items.json"
TASKS_DIR = ROOT / "tasks"

DIAL_LEVELS = ["none", "low", "medium", "high"]
DIAL_R = 3
DESCRIPTION = (
    "Reasoning Dial: accuracy, output tokens and cost at one reasoning-effort level "
    "(see task name) on three seeded task families: Deduce, Arith, Distract."
)
CALIBRATION_DESCRIPTION = "Reasoning Dial calibration (private): calibration items at none and high."


def _items_block(items) -> str:
    if items is None:
        return "ITEMS = []  # PLACEHOLDER: test items are inlined at M4 from data/test_items.json"
    return "ITEMS = " + pprint.pformat(items, width=100, sort_dicts=False)


def render(*, name: str, description: str, levels: list[str], r: int,
           cache_probe: bool, items) -> str:
    inner = name.replace("dial-", "dial-call-", 1)
    out = TEMPLATE.read_text(encoding="utf-8")
    subs = {
        "@@LEVELS@@": json.dumps(levels),
        "@@R@@": str(r),
        "@@CACHE_PROBE@@": str(cache_probe),
        "@@PARSER@@": PARSER.read_text(encoding="utf-8").rstrip() + "\n",
        "@@ITEMS@@": _items_block(items),
        "@@INNER_DECORATOR@@": f"@kbench.task(name={json.dumps(inner)}, store_task=False, store_run=False)",
        "@@DECORATOR@@": f"@kbench.task(name={json.dumps(name)}, description={json.dumps(description)})",
    }
    for k, v in subs.items():
        assert out.count(k) == 1, k
        out = out.replace(k, v)
    return out


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def build() -> list[Path]:
    TASKS_DIR.mkdir(exist_ok=True)
    test_items = _load(TEST_ITEMS)
    written = []
    for level in DIAL_LEVELS:
        path = TASKS_DIR / f"dial_{level}.py"
        path.write_text(render(name=f"dial-{level}", description=DESCRIPTION, levels=[level],
                               r=DIAL_R, cache_probe=False, items=test_items),
                        encoding="utf-8", newline="\n")
        written.append(path)
    cal = _load(CALIBRATION_ITEMS)
    if cal is None:
        raise FileNotFoundError(f"{CALIBRATION_ITEMS} missing; run dial.generate first")
    path = TASKS_DIR / "dial_calibration.py"
    path.write_text(render(name="dial-calibration", description=CALIBRATION_DESCRIPTION,
                           levels=["none", "high"], r=1, cache_probe=True, items=cal),
                    encoding="utf-8", newline="\n")
    written.append(path)
    return written


if __name__ == "__main__":
    for p in build():
        print(f"wrote {p.relative_to(ROOT)}")
