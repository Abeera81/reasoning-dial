# Review Checklist

Do not mark work complete until the relevant checks pass.

## Basic Checks

- [ ] Diff is focused on the current milestone.
- [ ] No unrelated files were rewritten; generated `tasks/*.py` were regenerated, not hand-edited.
- [ ] `.env` and API keys not committed or printed.
- [ ] No `kaggle b t run` / `publish` without explicit approval and a spending limit in the current prompt.
- [ ] `python -m pytest -q` passes, or failures are explained.

## Validity Checks

- [ ] `data/test_items.json` unchanged since the lock (`git diff data/` clean; SHA-256 matches `data/test_items.sha256`).
- [ ] Prompt suffix, parser rules and analysis rules unchanged since the lock, or the change is logged in `MEMORY.md`.
- [ ] Every item's answer is computed by code and verified independently in tests.
- [ ] All four dial task files are identical except the `LEVEL` line (`tests/test_build.py`).
- [ ] No LLM judge; grading is deterministic.
- [ ] Every reported difference has n and a 95% CI; Holm applied; nothing inside the noise floor is claimed.
- [ ] Format failures and api_errors are reported separately from wrong answers.
- [ ] Temperature limitation disclosed; Gema et al. 2025 cited.

## Budget Checks

- [ ] Projected spend checked against §7 before any approved run; quota page checked before each batch.
- [ ] Actual quota used recorded in `MEMORY.md`.

## Security

Not applicable beyond secrets handling: no web app, endpoints, or user input.

## Final Evidence

The final response should include:

- Files changed
- Commands run and test output
- Quota spent (if any)
- Deviations from the Tech Design and why
- Remaining risks
