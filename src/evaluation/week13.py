"""Freeze retrospective Week 13 prediction cohorts and evaluate them against later observations."""

import argparse
import json
from pathlib import Path

from src.pipeline.monitoring_metrics import instant, performance, probability_errors

WINDOW = {"start": "2026-11-23T00:00:00Z", "end": "2026-11-30T00:00:00Z"}
AS_OF = "2026-11-30T23:59:59Z"


def select(slate, batches):
    """Select earliest verified storage time per game from ordered, receipt-checked ledgers."""
    selected, conflicts, outside = {}, set(), set()
    original = {}
    if not batches or not batches[0]:
        raise ValueError("Original issued ledger is required.")
    model = batches[0][0]["model_reference"]
    for index, batch in enumerate(batches):
        if probability_errors(batch):
            raise ValueError("Invalid or duplicate predictions in one batch.")
        for row in batch:
            key = str(row["game_id"])
            if key not in slate:
                outside.add(key)
                continue
            if (str(row["season"]), str(row["week"])) != ("2026", "13") or row["model_reference"] != model:
                raise ValueError("Unexpected season, week or model.")
            issue, cutoff, kickoff = map(instant, (row["issue_time"], row["forecast_cutoff"], row["cutoff"]))
            if not issue < cutoff < kickoff:
                raise ValueError("Stored issue, run cutoff and kickoff must be strictly ordered.")
            if list(map(str, (row["home_id"], row["away_id"]))) != slate[key]:
                conflicts.add(key)
                continue
            if index == 0:
                original[key] = row
            previous = selected.get(key)
            if previous:
                if instant(previous["cutoff"]) != kickoff:
                    conflicts.add(key)
                if issue == instant(previous["issue_time"]) and row != previous:
                    raise ValueError("Ambiguous simultaneous predictions.")
            if previous is None or issue < instant(previous["issue_time"]):
                selected[key] = row
    if len(original) != len(batches[0]):
        raise ValueError("Original ledger does not match the frozen slate.")
    return {"slate_size": len(slate), "original": list(original.values()), "expanded": list(selected.values()),
            "expanded_conflicts": sorted(conflicts), "outside_slate": sorted(outside),
            "uncovered": sorted(set(slate) - set(selected))}


def evaluate(cohorts, outcomes):
    """Keep conflicted expanded matches unlabeled and apply the deployed evaluator to each cohort."""
    reports = {}
    for name in ("original", "expanded"):
        rows = cohorts[name]
        conflicts = set(cohorts["expanded_conflicts"]) if name == "expanded" else set()
        usable = [o for o in outcomes if str(o["game_id"]) not in conflicts]
        report = performance(rows, usable, [WINDOW], AS_OF, None)
        report.update(forecast_games=len(rows), slate_games=cohorts["slate_size"],
                      schedule_conflicts=sorted(conflicts))
        window = report["windows"][0]
        window["correct_picks"] = (round(window["metrics"]["accuracy"] * window["matched"])
                                   if window["metrics"] else None)
        reports[name] = report
    return reports


def main():
    """Write either frozen cohorts or scores to a new private JSON file."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    freeze = commands.add_parser("freeze")
    freeze.add_argument("slate", type=Path)
    freeze.add_argument("batches", nargs="+", type=Path)
    score = commands.add_parser("score")
    score.add_argument("cohorts", type=Path)
    score.add_argument("outcomes", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    def read(path):
        return json.loads(path.read_bytes())
    result = (select(read(args.slate), [read(p) for p in args.batches]) if args.command == "freeze"
              else evaluate(read(args.cohorts), read(args.outcomes)))
    with args.output.open("x") as target:
        json.dump(result, target, indent=2, allow_nan=False)
        target.write("\n")


if __name__ == "__main__":
    main()
