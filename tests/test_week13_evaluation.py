"""Offline cohort selection and later-outcome gates using fictional game IDs."""
import unittest

from src.evaluation.week13 import evaluate, select


def prediction(i, **changes):
    return dict(dict(game_id=str(i), season="2026", week="13", home_id="1", away_id="2",
                     cutoff="2026-11-26T00:00:00Z", forecast_cutoff="2026-11-23T22:30:00Z",
                     issue_time="2026-11-20T20:00:00Z", model_reference="synthetic",
                     run_id="first", home_win_probability=.75, away_win_probability=.25), **changes)


def outcome(row):
    return dict(row, start_date=row["cutoff"], observed_at="2026-11-29T12:00:00Z",
                completed=True, home_points=14, away_points=7)


class Week13Evaluation(unittest.TestCase):
    def test_expansion_overlap_and_unresolved_games(self):
        # Game 2 acquires a kickoff. Games 3 and 4 still lack kickoff and history.
        slate = {str(i): ["1", "2"] for i in range(1, 5)}
        first = prediction(1)
        later = prediction(1, issue_time="2026-11-23T20:00:00Z", run_id="second")
        cohorts = select(slate, [[first], [later, prediction(2)]])
        self.assertEqual(cohorts["uncovered"], ["3", "4"])
        self.assertEqual(cohorts["expanded"][0], first)
        result = evaluate(cohorts, [outcome(first)])
        self.assertEqual(result["original"]["forecast_games"], 1)
        window = result["expanded"]["windows"][0]
        self.assertEqual((window["matched"], window["coverage"], window["metrics"]), (1, .5, None))

    def test_postponement_and_performance_gates(self):
        rows = [prediction(i) for i in range(40)]
        cohorts = select({r["game_id"]: ["1", "2"] for r in rows}, [rows])
        labels = [outcome(r) for r in rows[:32]]
        labels[-1]["start_date"] = "2026-11-27T00:00:00Z"
        self.assertIsNone(evaluate(cohorts, labels)["original"]["windows"][0]["metrics"])
        labels[-1] = outcome(rows[31])
        window = evaluate(cohorts, labels)["expanded"]["windows"][0]
        self.assertEqual((window["metrics"]["accuracy"], window["metrics"]["brier_score"]), (1, .0625))

    def test_conflicting_schedule_and_late_storage(self):
        row = prediction(1)
        changed = prediction(1, cutoff="2026-11-27T00:00:00Z", issue_time="2026-11-21T00:00:00Z")
        cohorts = select({"1": ["1", "2"]}, [[row], [changed]])
        self.assertEqual(cohorts["expanded_conflicts"], ["1"])
        self.assertEqual(evaluate(cohorts, [outcome(row)])["expanded"]["matched"], 0)
        with self.assertRaises(ValueError):
            select({"1": ["1", "2"]}, [[prediction(1, issue_time=row["cutoff"])]])
