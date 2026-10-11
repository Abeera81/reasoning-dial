# Reasoning Dial

Reasoning Dial is a Kaggle benchmark about one setting developers choose blind: **reasoning effort** (`none` / `low` / `medium` / `high`). It holds everything else fixed (same items, same prompt, same grader) and measures what turning the dial actually changes: accuracy, output tokens, and cost per correct answer, on three kinds of task. It also asks whether the dial is even the same instrument across vendors.

- Kaggle benchmark: https://www.kaggle.com/benchmarks/abeeralodhi/reasoning-dial
- Kaggle tasks (public): [dial-none](https://www.kaggle.com/benchmarks/tasks/abeeralodhi/dial-none/1) · [dial-low](https://www.kaggle.com/benchmarks/tasks/abeeralodhi/dial-low/1) · [dial-medium](https://www.kaggle.com/benchmarks/tasks/abeeralodhi/dial-medium/1) · [dial-high](https://www.kaggle.com/benchmarks/tasks/abeeralodhi/dial-high/1)
- Source: https://github.com/Abeera81/reasoning-dial
- Pre-registration (hypotheses, analysis plan, deviations): [`docs/PREREGISTRATION.md`](docs/PREREGISTRATION.md)

## Design

| | |
|---|---|
| Task families | **Deduce**: 7-person, 7-day scheduling puzzles with exactly one solution (checked by brute force). **Arith**: 6-step word problems with a percentage and an exact division (control family). **Distract**: count the objects you own while ignoring distractors (after Gema et al. 2025). 20 items per family. |
| Dial levels | `none`, `low`, `medium`, `high`, passed as `llm.prompt(..., reasoning=<level>)` (sent to providers as `reasoning_effort`). One Kaggle task per level: `dial-none`, `dial-low`, `dial-medium`, `dial-high`. |
| Repeats | 2 per item × level × model (`seed = 1000 + repeat`); temperature cannot be set on Kaggle. |
| Grading | Deterministic only. The model ends with `FINAL ANSWER: <x>`; our parser (`src/dial/parse.py`) strips `<think>` blocks and classifies each call as correct / wrong / format_fail / api_error. No LLM judge. |
| Locked items | `data/test_items.json`, generated from seed 2026 and committed with its SHA-256 (`data/test_items.sha256`) **before** any main-run call. Difficulty was tuned only on separate calibration seeds (1001, 1002). |
| Statistics | Item-cluster bootstrap 95% CIs; paired Wilcoxon on per-item correctness with Holm correction; pre-registered dial-behaviour labels. See the pre-registration. |

### Lineup

| Model | Levels | Note |
|---|---|---|
| gpt-oss-120b | low, medium, high | Rejects `none` (HTTP 400); its baseline is `low`. |
| gpt-5.4-mini-2026-03-17 | none, low, medium, high | |
| claude-haiku-5-5 | none, low, medium, high | |
| gemini-3.7-flash | none, low, medium, high | Kaggle's default model; runs on every task push. |

**Dropped:**

- **gemini-3.1-pro-preview:** budget. Its cost per call at high was roughly 5× the others, which does not fit the $10/day Kaggle quota next to the rest of the lineup.
- **claude-sonnet-5-default:** platform quota reservation. Kaggle reserves the *maximum* possible cost of every call up front (input + 128K output tokens × price, ≈ $1.28 per Sonnet call). With 8 calls in parallel that is ≈ $10.24, above the $10 daily quota. Fixing it would have meant editing the locked task files. Decided after the lock, before any Sonnet main-run data existed.

DeepSeek-R1, Grok 4.20 Non-Reasoning and gemini-3.8-flash appear only in the pilot or calibration notes.

## Reproduce

Python 3.14 was used. All commands run from the repository root (Git Bash or any POSIX shell).

```bash
# 1. Install the pinned dependencies
python -m pip install -r requirements.txt

# 2. Run the tests (generators verified by independent brute force / recomputation,
#    parser cases, task-file build checks, analysis on synthetic data)
python -m pytest -q

# 3. Rebuild every table and figure from the raw Kaggle run files in results/main/
python analysis/analyze.py
#    -> results/calls.csv, results/summary.md, analysis/figures/fig1..fig5 *.png
```

### Regenerate the test items and check the hash

```bash
PYTHONPATH=src python -m dial.generate /tmp/test_items.json 20 2026
sha256sum /tmp/test_items.json          # must equal the hash in data/test_items.sha256
(cd data && sha256sum -c test_items.sha256)   # checks the committed file: "test_items.json: OK"
```

Expected SHA-256: `90dd54981bb26f5c8a90ac7b61e86ac373e853e696d0833090d0483709790042`.

### Rebuild the Kaggle task files

```bash
PYTHONPATH=src python -m dial.build_tasks   # writes tasks/dial_*.py with items + parser inlined
```

Running tasks on Kaggle needs a Kaggle account and spends Kaggle AI quota; see `AGENTS.md` for the platform gotchas (UTF-8 mode for `kaggle b t push` on Windows, the hourly model-proxy key, quota reservations).

## Folder map

```
README.md, LICENSE, requirements.txt
docs/
  PREREGISTRATION.md        hypotheses, locked design, analysis plan, deviations/amendments
  PRD-ReasoningDial-MVP.md  product requirements
  TechDesign-ReasoningDial-MVP.md   technical design and milestones
  research-ReasoningDial.md background research and prior work
src/dial/
  generate.py               seeded generators: deduce, arith, distract
  parse.py                  answer parser (inlined verbatim into every task file)
  build_tasks.py            writes tasks/*.py from task_template.py.txt
data/
  test_items.json (+ .sha256)          locked test set, seed 2026
  calibration_items_seed1001/1002.json calibration sets (never used for results)
tasks/                      generated Kaggle task files (dial-none/low/medium/high, dial-calibration)
analysis/
  analyze.py                full analysis: CSV, summary, figures
  calibration_report.py, main_report.py   quick status reports
  figures/                  fig1-fig5
results/
  main/                     raw Kaggle run files for the main run (the analysis input)
  calibration/, calibration2/, smoke/   calibration and smoke-test run files
  calls.csv, summary.md     generated by analyze.py
  superseded.json           run files excluded from analysis, with reasons
tests/                      pytest suite
pilot/                      the original feasibility pilot (code + run files), read-only
AGENTS.md, CLAUDE.md, MEMORY.md, REVIEW-CHECKLIST.md, agent_docs/   working notes for AI coding agents
kaggle_benchmarks_reference.md   kaggle-benchmarks syntax notes
```

## Credits

- The Distract family and hypothesis H2 build on **Gema et al., *Inverse Scaling in Test-Time Compute*, arXiv:2507.14417 (2025)**, which found that longer reasoning can lower accuracy on simple counting tasks with distractors. Our items are modelled on that idea, not copied.
- Built on Kaggle Benchmarks (`kaggle-benchmarks`) and the Kaggle CLI.
- **Claude and Claude Code (Anthropic) were used** to help design, write and review the code, tests, analysis and documentation in this repository. All design decisions were made and approved by the author.

## License

MIT, see [LICENSE](LICENSE).
