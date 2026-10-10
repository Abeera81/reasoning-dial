# Pre-registration — Reasoning Dial

**Date:** 2026-10-10 (Asia/Karachi). Written and committed **before** any main-run task was pushed or run.
**Source of truth for the analysis.** Any later change to the prompt suffix, parser rules or analysis rules is logged with date and reason in `MEMORY.md` and disclosed in the article.

## 1. Locked test set

| | |
|---|---|
| File | `data/test_items.json` |
| SHA-256 | `90dd54981bb26f5c8a90ac7b61e86ac373e853e696d0833090d0483709790042` (also in `data/test_items.sha256`) |
| Generator | `src/dial/generate.py` at this commit, `generate_all(20, 2026)` |
| Items | 60: 20 Deduce, 20 Arith, 20 Distract |
| Seed | 2026 (each family uses `random.Random(f"{family}:2026")`) |

Calibration sets, never used for results: seed 1001 (calibration 1, pre-retune generator, `data/calibration_items_seed1001.json`) and seed 1002 (calibration 2, Deduce + Arith only, `data/calibration_items_seed1002.json`).

## 2. Hypotheses (from the PRD; hypotheses until the data decide)

- **H1 — The dial is not one instrument.** Output tokens rise from the lowest to the highest level for some models, while others stay flat, collapse levels, or reject a level.
- **H2 — More thinking can hurt on distractor counting.** On Distract, at least one dial-honoring model is less accurate at high than at its lowest level (prior: Gema et al. 2025).
- **H3 — More thinking helps on deduction.** On Deduce, accuracy rises from the lowest level to high for dial-honoring models. Prior work found inverse scaling on some constraint-tracking deduction, so Deduce may go either way. **Arith is not used for H3** (see §3).
- **H4 — The bill.** Where accuracy does not rise, cost per correct answer still does. **Arith is the control family for H4.**

## 3. Families and the role of Arith

- **Deduce** (test family for H1, H3, H4): 7 people, 7 consecutive days Monday–Sunday, one talk per day. Clue types: `not_on`, `before`, `immediately_before`, `not_adjacent`; no `on()` clues. Clues are added in random order until brute force over all 7! assignments gives exactly one solution, then any clue whose removal keeps the solution unique is removed. The question asks who speaks on a random day from Tuesday to Saturday.
- **Arith** (control family): 4 templates (warehouse, fuel, savings, recipe); each problem is 6 operations including at least one percentage step and one exact division; all intermediates are positive integers of at most 5 digits; the final answer has 4–6 digits. **Pre-registered expectation: accuracy at ceiling at every level.** Arith tests H4 (cost rises without accuracy gain) and is not used for H3. This role was decided after calibration 2 showed a none-level median of 1.00 and before any test item existed.
- **Distract** (test family for H2, H4): you own k ∈ {2,3,4,5} distinct objects of one category; 1–3 distractors from {probability about an owned object, unrelated numeric fact, someone else's math problem, a short code snippet}; question "Calculate how many <category> you have."; answer k. Generator check: outside the first sentence and the question, none of "you have", "you own", "you also", "you get", "gives you", "you buy", "you receive", "you lose", "you eat" appear.

Every answer is computed by code and verified independently in `tests/test_generate.py` (independent brute force for Deduce from the prompt text; independent recomputation for Arith from the prompt numbers).

## 4. Lineup, levels, repeats

| Model | Levels run | Primary comparison | Notes |
|---|---|---|---|
| gpt-oss-120b | low, medium, high | **high − low** | Rejects `none` (HTTP 400, allowed: high, low, max, medium, minimal). `minimal` is not used. |
| gpt-5.4-mini-2026-03-17 | none, low, medium, high | high − none | |
| claude-haiku-5-5 | none, low, medium, high | high − none | |
| claude-sonnet-5-default | none, low, medium, high | high − none | |
| gemini-3.7-flash | none, low, medium, high | high − none | Kaggle's default model; runs automatically when each dial task is pushed ("push validation run"). |

- Levels: `none`, `low`, `medium`, `high` via `llm.prompt(prompt, reasoning=<level>, seed=1000 + r)`; sent to the provider as `reasoning_effort`.
- **R = 2** repeats per item × level × model (budget cut step 1, see §8). 20 items per family.
- Temperature is not set (kaggle-benchmarks drops it on Kaggle). `google/*` models also drop `seed`, so Gemini repeats send identical requests.
- Excluded, reported from pilot data only: DeepSeek-R1 (ignores the dial, costly), Grok 4.20 Non-Reasoning (rejects the parameter), gemini-3.1-pro-preview (budget), gemini-3.8-flash (redundant with gemini-3.7-flash).
- For gpt-oss-120b, every reference below to "none" as the baseline level means "low".

## 5. Prompt and parser (frozen)

Each item prompt = body + this exact suffix, identical at every level:

```
Answer instruction: <"Answer with the person's name." | "Answer with a whole number.">

End your response with a final line in exactly this format:
FINAL ANSWER: <answer>
```

Parser (`src/dial/parse.py`, inlined verbatim into every task file):

1. **Think stripping:** remove every `<think>…</think>` block (case-insensitive). An unclosed `<think>` removes everything from it to the end of the text. A stray `</think>` with no opener removes everything before it. (The library already strips closed think blocks when reasoning ≠ none; at `none` they can remain.)
2. **Strict extraction:** take the **last** match of `FINAL ANSWER` + optional markdown (`*`, `_`, `` ` ``) + `:` or `：`, and the rest of that line. This handles `**FINAL ANSWER:** 42` and `**FINAL ANSWER**: 42`.
3. **Empty-marker rule (added 2026-10-10, before the lock, after calibration 1 showed `Ben\n\nFINAL ANSWER:`):** if the rest of the line after the last marker is empty after cleaning, use the last non-empty line before that marker (ignoring lines that are only markdown).
4. **Cleaning:** strip markdown (`*`, `_`, `` ` ``), quotes, and trailing `.` `,` `!`.
5. **Normalization:** `int`: remove thousands commas, take the first integer (leading `-` allowed); `"1,234."` → 1234. `name`: case-insensitive whole-word match against the 8 names Ana, Ben, Cleo, Dev, Eli, Fay, Gus, Hana; exactly one distinct name must appear, otherwise unparseable.
6. **Lenient extraction (secondary only):** if strict extraction is unparseable, apply step 5 to the last non-empty line of the visible text.
7. **Outcomes:** `api_error` (the model call raised), `format_fail` (strict extraction unparseable), `correct`, `wrong`.

**Primary accuracy** = correct / (all calls except api_error); format failures count as incorrect. **Secondary accuracy** uses lenient extraction. Both are reported. No LLM judge anywhere.

## 6. Analysis plan (Tech Design §6, unchanged)

Input: downloaded run files. Output: `results/calls.csv`, `results/summary.md` (every number the article will use), `analysis/figures/*.png`. Per-call records come from `subruns[].results[0].dictResult`; conversations are the fallback.

1. **Accuracy** per model × family × level, with 95% CI from an item-cluster bootstrap (resample items, keep all repeats of a resampled item; 5,000 reps; `numpy` seed 0).
2. **Primary test (H2, H3):** per model × family, Δ = accuracy(high) − accuracy(none), paired by item. Wilcoxon signed-rank on per-item mean correctness, Holm correction across all model × family pairs, plus bootstrap CI on Δ. A difference is called an effect only if the Holm-adjusted p < 0.05 **and** the CI excludes 0.
3. **Dial behavior (H1):** median output tokens per model × level. Pre-stated labels: *honors* = medians non-decreasing none→high and high/none ≥ 1.3; *ignores* = high/none < 1.15; *collapsed levels* = adjacent levels within 5% of each other; *rejects* = api_error on that level. ~~Think-chars reported alongside as an independent check.~~ Reasoning-trace length (`kbench.last_reasoning_traces()`) is reported alongside as a partial check (decided after M0: think tags are stripped by the library, and only some providers return traces).
4. **Cost (H4):** cost per correct answer per model × family × level.
5. **Format:** format_fail rate per model × level; strict vs lenient accuracy side by side.
6. **Noise floor:** per model × family × level, accuracy in each repeat and the range; per-item flip rate across repeats; count of byte-identical repeat responses (caching check).
7. **Figures** (matplotlib, 1600 px wide, one fixed color per model across all figures, colorblind-safe): fig1 dial curves (accuracy vs level, one panel per family, one line per model, CI bands); fig2 token ladder (median output tokens vs level per model, log y); fig3 cost per correct vs level; fig4 forest plot of Δ(high − baseline) with CIs per model × family; fig5 format-failure table/heatmap by model × level.

Application notes (not changes): for gpt-oss-120b the baseline level is `low` in items 2–3. Arith Δs are computed and reported but are not tests of H3. The Holm family is all model × family pairs, Arith included.

## 7. Budget and run order

- Kaggle AI quota $10/day. Batch 1 (2026-10-10): push the four dial tasks (each push runs gemini-3.7-flash), then gpt-oss-120b (low/medium/high), claude-haiku-5-5, gpt-5.4-mini-2026-03-17; cap $5.00. Batch 2 (after quota reset): claude-sonnet-5-default.
- Projection at R = 2, 20 items/family (calibration costs): gpt-oss $0.46, haiku $0.16, gpt-5.4-mini $1.12, sonnet $5.77, push runs (gemini-3.7-flash) $2.31.

## 8. Budget cut order (Tech Design §7)

R 3 → 2 (**applied**); then drop gemini-3.1-pro-preview (already dropped); then 20 → 15 items per family, taking the first 15 of each family from the locked file with no regeneration. Levels and families are never cut.

## 9. Known before lock

Everything below was observed on calibration or pilot items before the test set existed; none of it is a finding from the test set.

- **Pilot (2026-10-10, 10 easy items, 8 models):** output tokens rose with the level for gpt-oss-120b (2.9×), gpt-5.4-mini, Gemini 3.8 Flash, Gemini 3.1 Pro, Gemini 3.7 Flash; Claude Sonnet 5 low = medium; Claude Haiku 5.5 and DeepSeek-R1 flat or falling; Grok 4.20 Non-Reasoning rejected `reasoning_effort`.
- **Calibration 1 (seed 1001, old generator, none + high):** every model ≈ 100% at none on Deduce (N = 5) and Arith (4–5 steps) except gpt-5.4-mini (Deduce 0.25, Distract 0.75 at none, ~17 output tokens). gpt-oss-120b rejects `none`. On Distract at high, gpt-oss-120b scored 0.38, counting distractors as owned items (answers 999, 434, 14); Sonnet 0.88 (counted a code list). gpt-oss produced 4 empty-marker replies (led to the parser rule in §5.3). No caching (`enable_caching=False`; identical replies only when trivially short).
- **Calibration 2 (seed 1002, retuned, Deduce + Arith, none + high):** none-level Deduce: haiku 0.88, sonnet 1.00, gpt-5.4-mini 0.12, gemini-3.7-flash 1.00 → median **0.88 on the named lineup, 0.94 with gemini-3.7-flash**. Arith: 1.00 for every model at none → reclassified as the control family. At high every model ≥ 0.88. Deduce output tokens roughly doubled to tripled vs calibration 1.
- **Gemini at `none`** spends ~300–1,400 output tokens with no trace text and a one-line reply (hidden thinking at `none`).

## 10. Deviations from the Tech Design so far

1. **Nested task design:** each dial file defines an inner per-call task `dial-call-<level>` (`store_task=False, store_run=False`) run via `evaluate(..., n_jobs=8, on_failure="continue")`; the outer `dial-<level>` returns primary accuracy (`-> float`). Per-call records live in `subruns`. (TD §5 described a single loop.)
2. **Dial files differ in 3 lines, not 1:** `LEVELS`, and the two `@kbench.task(name=...)` lines, because the push CLI reads task names as string literals.
3. **think_chars dropped as a metric**; output tokens are the primary dial signal; reasoning-trace length is a partial check.
4. **Parser additions:** stray `</think>` handling; empty-marker rule (§5.3); names matched against all 8 names.
5. **Seeding:** each family uses `random.Random(f"{family}:{seed}")`.
6. **Retune beyond TD's suggestion:** Deduce N = 7 with no `on()` clues (TD: N = 6 or fewer on/not_on clues); Arith 6 operations with percentage + division, 4–6 digit answers (TD: 5 steps, larger numbers).
7. **Calibration 2** covered Deduce and Arith only, without a cache probe; gemini-3.8-flash was not run in it (spend cap).
8. **Difficulty gate:** TD target 30–85%; the user set 20–90% for the retune decision. Arith failed and became the control family; Deduce was evaluated on the named lineup.
9. **R = 2** (TD default R = 3).
10. **Lineup:** gemini-3.1-pro-preview and gemini-3.8-flash dropped; gemini-3.7-flash included via push validation runs; gpt-oss-120b runs low/medium/high with high − low as its primary comparison.
11. **Temperature** is not set (not possible on Kaggle); `google/*` models also drop `seed`.
12. **Tooling:** `kaggle b t push` on Windows needs `PYTHONUTF8=1`; `analysis/calibration_report.py` added for calibration summaries.
