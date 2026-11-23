# Week 13 pregame update and November 30 evaluation

## Saved evidence, reconciled November 22, 2026

The fixed slate is the 65 unique 2026 Week 13 game IDs in the November 20 capture. The November 21 roster agrees. Each prediction CSV was read from private storage, verified against its own weekly summary and joined by game ID. All 53 predictions overlap. Home and away IDs, recorded kickoffs and the protected model reference agree on every overlap. The union is **53/65 (81.54%)**. The files have distinct source identities. Storage issue times below are the prediction object's UTC LastModified, rather than the time the schedule was retrieved.

| Run | Stored UTC | Run cutoff UTC | Prediction CSV SHA-256 |
|---|---|---|---|
| pm05-week13-fresh-20261120 | Nov 20 22:16:09 | Nov 20 23:59 | adb4c89506673dc186132a09be04f97bb4b7f26394efe233bd4328eb10f3d289 |
| pm07b-week13-paired-20261121 | Nov 21 05:27:00 | Nov 21 18:00 | d42fb929db652b124e00652c71f8639eb742a0b0dbd91da45355d7c96a812b89 |

Both eligibility records identify these same twelve unscored games. Matchups are away at home.

| Game ID | Matchup | Reason in both captures |
|---|---|---|
| 401856757 | Auburn at Alabama | TBD kickoff |
| 401856758 | LSU at Arkansas | TBD kickoff |
| 401856760 | Georgia Tech at Georgia | TBD kickoff |
| 401856761 | Louisville at Kentucky | TBD kickoff |
| 401856764 | South Carolina at Clemson | TBD kickoff |
| 401856765 | Tennessee at Vanderbilt | TBD kickoff |
| 401858312 | Duke at Wake Forest | TBD kickoff |
| 401858316 | SMU at Stanford | TBD kickoff |
| 401858538 | Purdue at Indiana | TBD kickoff |
| 401858541 | Washington at Oregon | TBD kickoff |
| 401864549 | North Dakota State at San José State | Missing away-team prior history |
| 401864547 | Sacramento State at Hawai'i | Missing away-team prior history |

The saved scored kickoffs range from Nov 25 00:00 through Nov 29 02:30 UTC. These are dated schedule observations. The ten TBD games could gain coverage if a fresh capture resolves their kickoffs and all eligibility checks pass. The other two still lack history under the fixed historical selection.

## Proposed execution, pending approval

Use the existing us-east-1 Standard workflow fbs-weekly-pipeline. No deployment change is needed. On Monday, November 23, start between **4 p.m. and strictly before 5 p.m. EST (21:00–22:00 UTC)**. The fixed cutoff is **5:30 p.m. EST / 22:30 UTC**. The half-hour reserve is a stop margin, not a runtime guarantee. If approval or preflight misses the start window, do not launch. Report remaining candidates from the last dated evidence, distinguish unknown starts, and obtain a separately approved prospective cutoff before further capture.

* Submit exactly one StartExecution, name and run token `pm16-week13-20261123`, ingestion token `pm16-week13-capture-20261123`. The prepared private input is `data/processed/pm16-week13/weekly-request.json`, SHA-256 `b0f891b726af6caddc57e1b97ca0d6db291f5502fb8fe5080ee8d606a89a680f`. It selects 2026 Week 13, fresh capture, the five previously verified history sources, the November 21 summary as previous schedule, the same protected model and retrospective mode.
* Immediately before start, check UTC, FREE/ACTIVE status, eligible credit balance and coverage for the bounded workflow, Lambda, secret access, storage and logs including retention. Stop for insufficient evidence of zero personal payment. Verify deployment identities, existing scoped permissions, disabled schedule, unused tokens/output namespace, pinned history/model/previous summary and event digest. Journal the single attempt before submission.
* Limits: one workflow execution, normally four weekly worker calls (ingest, prepare, infer, finalize), hard ceiling eight under the deployed seven-poll budget, one ingestion invocation, one CFBD HTTP attempt, at most one saved-model scoring batch. Zero odds, queries, model fits, outcome captures, monitoring/publication or other workload calls. Additional pending polls may only inspect the original capture intent/receipt; its conditional claim prevents duplicate ingestion. Stop on an ambiguous invocation. The worker scores its whole eligible input. Required writes are fresh private capture claim/raw/manifest/receipt, weekly claim, ingestion reference, normalized records, dataset, eligibility, stage receipts, prediction CSV/provenance, final summary and ordinary execution logs. Preserve both prior runs and protected model objects.
* Check the actual capture time, receipt bindings, row accounting, prior and new schedule identities, model hash, per-stage hashes, valid complementary probabilities and durable storage time before cutoff and each kickoff. Compare new IDs with the frozen 65 and prior 53, enumerate remaining exclusions with reasons, and report any outside-slate games separately. Verify cumulative calls and unchanged prior artifacts. Never count a late or ambiguous issue as pregame. Preserve retrospective/withheld status even for a completed workflow.
* On expiry, integrity failure, budget breach or ambiguity, stop further work, stop an active execution if needed, preserve evidence and inspect the original execution read-only. No replacement token, retry, backdating, cutoff change or relaxation. Report zero new coverage if that is the observed result.

## Frozen evaluation rule

Lock both ledgers before examining outcomes. Original means exactly the 53 issued on Nov 20. Expanded selects the earliest eligible, verifiably stored prediction per game across Nov 20, Nov 21 and the single approved update if it succeeds. Store full source run ID, game ID and sides, issue time, run cutoff, captured kickoff, protected model/receipt and probabilities. Use the hash-checked prediction CSV plus its S3 storage timestamp and bound request to construct each ledger. A tied ambiguous issue stops selection. Flag changed sides/kickoffs, withhold uncertain expanded matches, and retain covered games in the coverage denominator. Extra slate IDs are reported separately. Do not replace predictions after observing results.

Private inputs in `data/processed/pm16-week13/` are frozen through November 21. SHA-256 for slate.json is `08464c6423a04c92fad9fc9774738b3d454ef73aa6d721872b75e12996125a85`. For issued-20.json and issued-21.json the hashes are `03bff97dfadfc3d9a8184633b022924e8e571431a431aa9fc04e0dd941628c03` and `663cc4546155d779a4ac1879358db74968c5d3362aee0fc4aba6eb53c22c04c9`. When an update is verified, add its similarly bound ledger, hash the inputs and freeze once to a fresh output. If the update was skipped, use the existing frozen-through-nov21.json.

From the repository root, with the private files available:

```bash
d=data/processed/pm16-week13
.venv/bin/python -B -m src.evaluation.week13 --output "$d/frozen-final.json" freeze \
  "$d/slate.json" "$d/issued-20.json" "$d/issued-21.json" "$d/issued-update.json"
```

On November 30, obtain separate authorization for a dated later-outcome snapshot. Preserve its raw bytes, receipt, observation time and hashes. Prepare outcome records with game_id, season, week, home_id, away_id, completed, start_date, observed_at and both scores. Apply the frozen ledger; retain unmatched, incomplete and postponed games in the accounting. Score only observations collected by November 30 23:59:59 UTC; defer if a usable snapshot is unavailable by then.

```bash
.venv/bin/python -B -m src.evaluation.week13 --output "$d/evaluation.json" score \
  "$d/frozen-final.json" "$d/outcomes.json"
```

The [existing evaluator](../src/pipeline/monitoring_metrics.py) uses a half-open **kickoff** window, here Nov 23 00:00 inclusive through Nov 30 00:00 UTC exclusive. Report any out-of-window predictions separately. It selects the latest observation per ID by as-of, refuses conflicting same-time records, and requires completed non-tied games, matching season/week/sides and exact kickoff, with observation strictly after kickoff. Report separately for each cohort:

* Forecast coverage = distinct issued games / 65. The frozen original is 53/65.
* Outcome coverage = matched outcomes / eligible predictions inside the window. Flag postponed or uncertain matches and report pending/mismatched counts.
* With at least 30 matched labels and at least 80% coverage, report correct picks / matched outcomes, accuracy and mean squared probability error (Brier score). A home probability of at least 0.5 picks home. Otherwise report counts and pending/insufficient status. The 740-game historical holdout is a separate population.

No real outcomes were used in preparing this rule. Forecasts remain retrospective and operational approval remains withheld.
