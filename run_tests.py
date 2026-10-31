import csv
import os
import sys

from attacks import ATTACKS
from judge import leaked
from target import MODEL, ask_bot

LEVELS = [0, 1, 2]  # used when no levels are given on the command line
RUNS = 3  # the model's replies vary, so one try per attack could just be luck
RESULTS_DIR = "results"
COLUMNS = ["level", "attack_id", "category", "run", "raw_leaked", "final_leaked", "reply", "raw_reply"]


# Send every attack RUNS times at each level, judge each reply, and return one row per call
def run_all(model, levels):
    rows = []
    total = len(levels) * len(ATTACKS) * RUNS
    for level in levels:
        for attack in ATTACKS:
            for run in range(1, RUNS + 1):
                raw_reply, final_reply = ask_bot(attack["prompt"], level, model)
                row = {
                    "level": level,
                    "attack_id": attack["id"],
                    "category": attack["category"],
                    "run": run,
                    "raw_leaked": leaked(raw_reply),  # did the model try to leak?
                    "final_leaked": leaked(final_reply),  # did the leak reach the user?
                    "reply": final_reply,
                    "raw_reply": raw_reply,  # before the filter; differs from reply only at level 2
                }
                rows.append(row)
                verdict = "Secret has been leaked" if row["final_leaked"] else "Secret has not been leaked"
                print(f"[{len(rows):>3}/{total}] Level {level}  {attack['id']}  run {run}:  {verdict}")
    return rows


# Save every row to results.csv so the replies can be checked by hand later
def write_csv(rows, out_dir):
    with open(os.path.join(out_dir, "results.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


# Percentage of rows that leaked, with the count behind it, as text like "13% (2/15)"
def leak_rate(rows, column):
    if not rows:
        return "-"
    leaks = sum(1 for row in rows if row[column])  # True counts as one leak
    return f"{round(100 * leaks / len(rows))}% ({leaks}/{len(rows)})"


# One table row: leak rates at each level for the given rows (one category, or all of them)
def summary_line(name, rows):
    def at_level(level):
        return [row for row in rows if row["level"] == level]

    cells = [
        leak_rate(at_level(0), "final_leaked"),
        leak_rate(at_level(1), "final_leaked"),
        leak_rate(at_level(2), "raw_leaked"),  # what the model tried before the filter
        leak_rate(at_level(2), "final_leaked"),  # what got past the filter
    ]
    return f"| {name} | " + " | ".join(cells) + " |"


# Build the Markdown table: one line per category plus a total line
def build_summary(rows):
    categories = list(dict.fromkeys(attack["category"] for attack in ATTACKS))  # unique, in order
    lines = [
        "| Category | Level 0 | Level 1 | Level 2 (tried) | Level 2 (reached user) |",
        "| --- | --- | --- | --- | --- |",
    ]
    for category in categories:
        lines.append(summary_line(category, [row for row in rows if row["category"] == category]))
    lines.append(summary_line("**Total**", rows))
    return "\n".join(lines)


# Usage: python run_tests.py [model] [levels...]   e.g. python run_tests.py claude-haiku-4-5 0
if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else MODEL
    levels = [int(level) for level in sys.argv[2:]] or LEVELS  # "or" falls back when none are given
    out_dir = os.path.join(RESULTS_DIR, model)  # one folder per model, so runs don't overwrite each other
    os.makedirs(out_dir, exist_ok=True)
    rows = run_all(model, levels)
    write_csv(rows, out_dir)
    summary = build_summary(rows)
    with open(os.path.join(out_dir, "summary.md"), "w") as f:
        f.write(summary + "\n")
    print("\n" + summary)
