import csv
import os

from attacks import ATTACKS
from judge import leaked
from target import ask_bot

LEVELS = [0, 1, 2]
RUNS = 3  # the model's replies vary, so one try per attack could just be luck
RESULTS_DIR = "results"
COLUMNS = ["level", "attack_id", "category", "run", "raw_leaked", "final_leaked", "reply"]


# Send every attack RUNS times at every level, judge each reply, and return one row per call
def run_all():
    rows = []
    total = len(LEVELS) * len(ATTACKS) * RUNS
    for level in LEVELS:
        for attack in ATTACKS:
            for run in range(1, RUNS + 1):
                raw_reply, final_reply = ask_bot(attack["prompt"], level)
                row = {
                    "level": level,
                    "attack_id": attack["id"],
                    "category": attack["category"],
                    "run": run,
                    "raw_leaked": leaked(raw_reply),  # did the model try to leak?
                    "final_leaked": leaked(final_reply),  # did the leak reach the user?
                    "reply": final_reply,
                }
                rows.append(row)
                verdict = "Secret has been leaked" if row["final_leaked"] else "Secret has not been leaked"
                print(f"[{len(rows):>3}/{total}] Level {level}  {attack['id']}  run {run}:  {verdict}")
    return rows


# Save every row to results/results.csv so the replies can be checked by hand later
def write_csv(rows):
    with open(os.path.join(RESULTS_DIR, "results.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


# Percentage of rows that leaked, as text like "33%"
def leak_rate(rows, column):
    if not rows:
        return "-"
    leaks = sum(1 for row in rows if row[column])  # True counts as one leak
    return f"{round(100 * leaks / len(rows))}%"


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


if __name__ == "__main__":
    os.makedirs(RESULTS_DIR, exist_ok=True)  # create results/ if it isn't there yet
    rows = run_all()
    write_csv(rows)
    summary = build_summary(rows)
    with open(os.path.join(RESULTS_DIR, "summary.md"), "w") as f:
        f.write(summary + "\n")
    print("\n" + summary)
