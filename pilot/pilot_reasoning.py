# Syntax reference: kaggle_benchmarks_reference.md
# Feasibility pilot: is llm.prompt(..., reasoning=...) honored, i.e. does
# output-token use rise with the reasoning level?
import dataclasses
import re

import kaggle_benchmarks as kbench

LEVELS = ["low", "medium", "high"]

ITEMS = [
    # --- multi-constraint scheduling ---
    dict(
        id="sched-1",
        question=(
            "Four meetings A, B, C and D fill the slots 9:00, 10:00, 11:00 and 12:00, "
            "one meeting per slot. Constraints: A is earlier than B. C is at 11:00. "
            "D is not at 9:00. B is not at 12:00. Which meeting is at 12:00? "
            "Answer with the single letter only."
        ),
        answer="D",
    ),
    dict(
        id="sched-2",
        question=(
            "Five people P, Q, R, S and T each give one talk, one per day, Monday to "
            "Friday. Constraints: R speaks on Wednesday. P speaks on the day immediately "
            "before Q. T does not speak on Monday or Friday. S speaks on a later day than Q. "
            "Who speaks on Thursday? Answer with the single letter only."
        ),
        answer="T",
    ),
    dict(
        id="sched-3",
        question=(
            "One worker does three jobs back to back with no breaks, starting at 09:00. "
            "Job X takes 2 hours, job Y takes 1 hour, job Z takes 3 hours. Constraints: "
            "Z must be done last. Y must be done before X. At what hour on the 24-hour "
            "clock does job Z finish? Answer with the hour as an integer only (e.g. 17)."
        ),
        answer="15",
    ),
    dict(
        id="sched-4",
        question=(
            "Three meetings Alpha, Beta and Gamma are assigned to rooms 1, 2 and 3, one "
            "meeting per room. Constraints: Alpha is not in room 1. Alpha is not in room 3. "
            "Beta is in a higher-numbered room than Gamma. Gamma is not in room 2. "
            "Which room number is Beta in? Answer with the room number only."
        ),
        answer="3",
    ),
    # --- two-step arithmetic word problems ---
    dict(
        id="arith-1",
        question=(
            "Pens cost $3 each. Maria buys 7 pens and pays with a $50 bill. How many "
            "dollars of change does she get? Answer with the number only."
        ),
        answer="29",
    ),
    dict(
        id="arith-2",
        question=(
            "A train travels at 60 km/h for 2.5 hours, then at 80 km/h for 1.5 hours. "
            "How many kilometres does it travel in total? Answer with the number only."
        ),
        answer="270",
    ),
    dict(
        id="arith-3",
        question=(
            "A 240-litre tank is three-quarters full. Then 45 litres are drained out. "
            "How many litres remain in the tank? Answer with the number only."
        ),
        answer="135",
    ),
    # --- short passage reading ---
    dict(
        id="passage-1",
        question=(
            "Passage: The Larkspur Bridge, completed in 1887, spans the Orrin River. It "
            "was designed by engineer Helena Voss and was originally painted green before "
            "being repainted red in 1952.\n\n"
            "Question: In what year was the bridge repainted red? Answer with the year only."
        ),
        answer="1952",
    ),
    dict(
        id="passage-2",
        question=(
            "Passage: The village of Tamsworth holds its harvest fair every October. The "
            "fair's oldest event is the turnip-carving contest, first held in 1903. The "
            "2019 winner of the contest was a baker named Ottilie Marsh.\n\n"
            "Question: What was the profession of the 2019 winner? Answer with one word only."
        ),
        answer="baker",
    ),
    dict(
        id="passage-3",
        question=(
            "Passage: Kestrel Labs released three versions of its Finch sensor: Finch 1 "
            "in 2014, Finch 2 in 2017, and Finch 3 in 2021. Only Finch 2 was waterproof.\n\n"
            "Question: Which Finch version was waterproof? Answer with the version number only."
        ),
        answer="2",
    ),
]


@dataclasses.dataclass
class Answer:
    answer: str


def normalize(text) -> str:
    s = str(text).strip().lower()
    s = re.sub(r"^(the|finch|room)\s+", "", s)
    s = re.sub(r"[^a-z0-9.]", "", s).strip(".")
    try:
        f = float(s)
        if f == int(f):
            s = str(int(f))
    except ValueError:
        pass
    return s


@kbench.task(
    name="reasoning-pilot",
    description="Pilot: does output-token use rise with the reasoning level (low/medium/high)?",
    version=1,
)
def reasoning_pilot(llm) -> dict:
    # With reasoning set, Model Proxy returns "<think>...</think>{json}" and the
    # OpenAI SDK's native structured-output parser fails on it before kbench can
    # strip the think tags (and the call's token usage is lost). Use kbench's
    # prompted-JSON schema path instead: same schema, parsed after stripping.
    llm.support_structured_outputs = False
    calls = []
    for item in ITEMS:
        for level in LEVELS:
            rec = dict(item=item["id"], level=level, expected=item["answer"])
            with kbench.chats.new(f"{item['id']}-{level}") as chat:
                try:
                    obj = llm.prompt(
                        item["question"]
                        + "\nPut only the final answer in the answer field.",
                        schema=Answer,
                        temperature=0,
                        reasoning=level,
                    )
                    rec["got"] = obj.answer
                    rec["correct"] = normalize(obj.answer) == normalize(item["answer"])
                    rec["error"] = None
                except Exception as e:  # record and keep going
                    rec["got"] = None
                    rec["correct"] = False
                    rec["error"] = f"{type(e).__name__}: {e}"
                u = chat.usage
                rec["output_tokens"] = u.output_tokens
                rec["input_tokens"] = u.input_tokens
                rec["cost_usd"] = (
                    u.total_cost_nanodollars / 1e9
                    if u.total_cost_nanodollars is not None
                    else None
                )
            print(rec)
            calls.append(rec)

    summary = {}
    for level in LEVELS:
        rs = [c for c in calls if c["level"] == level]
        toks = [c["output_tokens"] for c in rs if c["output_tokens"] is not None]
        costs = [c["cost_usd"] for c in rs if c["cost_usd"] is not None]
        summary[level] = dict(
            accuracy=sum(c["correct"] for c in rs) / len(rs),
            mean_output_tokens=sum(toks) / len(toks) if toks else None,
            mean_cost_usd=sum(costs) / len(costs) if costs else None,
            n_errors=sum(c["error"] is not None for c in rs),
        )
        kbench.assertions.assert_true(
            summary[level]["n_errors"] == 0,
            expectation=f"All {len(rs)} calls at reasoning={level} succeed",
        )
    print(summary)
    return dict(summary=summary, calls=calls)


reasoning_pilot.run(kbench.llm)
