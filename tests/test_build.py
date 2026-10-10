"""Task-file checks. Files are parsed with ast and compared as text; they are never
imported, because importing one runs the task."""

import ast
import difflib
import json
import re
from pathlib import Path

import pytest

from dial import build_tasks as bt

ROOT = Path(__file__).resolve().parents[1]
DIAL_FILES = {lv: ROOT / "tasks" / f"dial_{lv}.py" for lv in bt.DIAL_LEVELS}
CAL_FILE = ROOT / "tasks" / "dial_calibration.py"


@pytest.fixture(scope="module", autouse=True)
def built():
    return bt.build()


def task_names(source: str) -> list[str]:
    """Same rule the Kaggle CLI uses: name= keyword constant on a *.task decorator."""
    names = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                func = dec.func if isinstance(dec, ast.Call) else dec
                if getattr(func, "attr", None) == "task" or getattr(func, "id", None) == "task":
                    names.append(next(k.value.value for k in dec.keywords if k.arg == "name"))
    return names


def test_files_written_and_parse():
    for path in [*DIAL_FILES.values(), CAL_FILE]:
        src = path.read_text(encoding="utf-8")
        ast.parse(src)
        assert src.rstrip().endswith("dial_task.run(kbench.llm)")


def test_dial_files_differ_only_in_level_and_names():
    base = DIAL_FILES["none"].read_text(encoding="utf-8").splitlines()
    for lv, path in DIAL_FILES.items():
        other = path.read_text(encoding="utf-8").splitlines()
        assert len(other) == len(base)
        changed = [(a, b) for a, b in zip(base, other) if a != b]
        if lv == "none":
            assert changed == []
            continue
        assert len(changed) == 3, list(difflib.unified_diff(base, other, lineterm=""))
        assert changed[0] == ('LEVELS = ["none"]', f'LEVELS = ["{lv}"]')
        assert changed[1][0].startswith('@kbench.task(name="dial-call-none"')
        assert changed[1][1] == changed[1][0].replace('"dial-call-none"', f'"dial-call-{lv}"')
        assert changed[2][0].startswith('@kbench.task(name="dial-none"')
        assert changed[2][1] == changed[2][0].replace('"dial-none"', f'"dial-{lv}"')


def test_task_names_match_push_slugs():
    for lv, path in DIAL_FILES.items():
        assert task_names(path.read_text(encoding="utf-8")) == [f"dial-call-{lv}", f"dial-{lv}"]
    assert task_names(CAL_FILE.read_text(encoding="utf-8")) == ["dial-call-calibration", "dial-calibration"]
    all_names = [n for p in [*DIAL_FILES.values(), CAL_FILE] for n in task_names(p.read_text(encoding="utf-8"))]
    assert len(all_names) == len(set(all_names))  # no collisions across files


def test_parser_inlined_verbatim():
    parser_src = (ROOT / "src" / "dial" / "parse.py").read_text(encoding="utf-8").rstrip()
    for path in [*DIAL_FILES.values(), CAL_FILE]:
        assert parser_src in path.read_text(encoding="utf-8")


def test_calibration_config_and_items():
    src = CAL_FILE.read_text(encoding="utf-8")
    assert 'LEVELS = ["none", "high"]' in src
    assert re.search(r"^R = 1$", src, re.M)
    assert re.search(r"^CACHE_PROBE = True$", src, re.M)
    tree = ast.parse(src)
    items = next(ast.literal_eval(n.value) for n in tree.body
                 if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "ITEMS")
    assert items == json.loads((ROOT / "data" / "calibration_items.json").read_text(encoding="utf-8"))


def test_dial_config():
    for path in DIAL_FILES.values():
        src = path.read_text(encoding="utf-8")
        assert re.search(r"^R = 3$", src, re.M)
        assert re.search(r"^CACHE_PROBE = False$", src, re.M)
        assert "temperature" not in src and "schema=" not in src
        if not (ROOT / "data" / "test_items.json").exists():
            assert "ITEMS = []  # PLACEHOLDER" in src
