# Monitoring findings - packet for Hampton's review

**Prepared November 21, 2026; no acknowledgment or investigation is asserted.**
The evidence is the saved PM-06 report as of **November 20, 2026, 22:30 UTC**
(5:30 p.m. Eastern), not a new measurement. This packet creates no review-handler
invocation, transition, incident closure, retraining decision or forecast approval.
Hampton may review it later and record only actions actually taken.

## Evidence and scope

The preserved original completion pins the report hash; saved replay returns the
same completion and report bytes. PM-10 locally rechecked those bindings without
calling AWS. Private paths, identifiers and detailed hash/receipt records remain
ignored. The [historical verification summary](cloud-monitoring-verification.md)
records cloud execution and replay; the [monitoring contract](monitoring-contract.md)
explains policy. Model and source values were not recomputed or refreshed.

The batch had **65 raw games, 55 retained, 10 quarantined, zero normalization
exclusions, two feature rejections for missing away-team history, and 53 technical
scoring rows**. Retained is a normalization count; it does not mean every row is
feature-eligible or approved for operational forecasting. Invalid features and
probabilities were both zero. The preserved verification contains no genuine-alert review chain; only the
earlier explicitly simulated alert has review transitions. This packet does not
establish whether Hampton later read anything off screen.

## 1. Quarantine warning

**Known.** Ten of 65 games were set aside for TBD kickoff times: **15.3846%**,
above the policy's **10%** warning threshold. Those records were not silently
assigned kickoff times or used as eligible scoring rows. This is a saved-data
quality warning, not proof of an ingestion outage or a current problem.

**Plausible explanations (not established findings).** A schedule provider may
not yet have resolved start times at capture. Revision timing or an upstream
representation change could also explain the missing values. The warning alone
does not distinguish these explanations.

**Unanswered.** Which source values lacked times at the approved capture? Were
the exclusions consistent with the preserved manifest/normalization quality
report? Did the provider later resolve them? Would a later, separately approved
capture satisfy that run's cutoff? The saved observation cannot answer what
changed afterward.

**Recommended action.** First inspect the already-preserved quarantine rows and
quality report off screen, confirm the ten-record accounting and reason, and
record actual findings if reviewed. Continue withholding those rows. Do not
invent times, relax eligibility, recapture automatically or classify the warning
as resolved. Any new capture requires its own bounded authorization and cutoff.

## 2. Feature-distribution warning

**Known.** Reference sample: **2,194 training rows (2022-2024)**. Scoring sample:
**53 saved rows**, above the policy minimum of **30**. `prior_win_pct_diff` had
population stability index (PSI) **0.2529945485983902**, above **0.20**. PSI compares
bin shares using training-derived cutpoints and smoothing; it is a descriptive
heuristic, not a hypothesis test or proof of declining accuracy.

| Other feature | Measured indicator | Threshold | Saved result |
| --- | --- | --- | --- |
| `prior_avg_margin_diff` | PSI 0.12048550080608399 | > 0.20 | No warning |
| `home_field` | Absolute rate difference 0.034184138559708255 | > 0.15 | No warning |

The win-rate means were approximately 0.02166 in training and 0.02820 in scoring;
similar means do not rule out different bin distributions. This is one small
weekly sample versus several training seasons, not evidence of concept drift.

**Plausible explanations (not established findings).** Matchup composition,
season-to-season schedule differences, a small 53-game sample, or the removal of
TBD/missing-history games could change bin shares. A feature-processing or source
revision issue is another possibility to rule out, not an observed defect.

**Unanswered.** Which bins account for the change? Are the selected prior-season
aggregates/hash identities correct? How sensitive is the result to sample size
and quarantine composition? Does any observed distribution change correspond to
measured prediction error once valid outcomes exist?

**Recommended action.** Inspect preserved bin counts/cutpoints and feature lineage
without fitting or changing thresholds. Compare like-for-like subsets only when
supported by existing evidence; otherwise propose a later bounded analysis.
Retain the warning and document uncertainty. Do not retrain, replace the model,
choose new features or claim predictive degradation on PSI alone.

## 3. Pending outcomes and unavailable performance

**Known.** There were **0 matched, 53 pending and 0 mismatched** outcome labels.
No later outcomes were selected. Batch-wide observed label coverage is **0/53**.
The fixed past window had **zero eligible kickoffs**, so its coverage and rolling
Brier/log-loss/accuracy/calibration are **null/unavailable**, not measured zero
performance. Pending labels do not show a model failure, perfect predictions or
an outcome-join defect.

**Plausible explanation.** This report deliberately selected a saved prediction
batch without later outcome captures. The timing of the fixed window also
explains its empty denominator; neither establishes current real-world game status.

**Unanswered.** Would later observations match game identity, orientation,
kickoff and publication boundaries? Would any revised/conflicting outcome be
rejected appropriately? Would a useful chronological window meet the configured
**30-label minimum** and **80% coverage** gate?

**Recommended action.** Leave rolling performance unavailable and operational
approval withheld. If later-outcome evaluation is needed, first obtain a bounded
capture/source-selection proposal; do not fetch now or substitute training/test
labels. The saved 2025 holdout (740 games) remains a historical reference, not a
replacement for rolling measurements. The five paired sportsbook comparisons
have no paired-outcome performance or market-outperformance conclusion.

## 4. Historical failure alert and genuine-review boundary

The separately preserved critical application-failure alert refers to an earlier
failed weekly execution. PM-06 demonstrated that a Lambda task returning HTTP
success with `state=failed` can still require an application alert. It is not a
new PM-10 incident. Any review should distinguish that historical failure from
the two saved-data warnings above and from the deliberately simulated smoke alert.
Do not close a genuine alert on the strength of a simulated review chain.

## Decisions Hampton can make after actually reviewing

- Confirm or question preserved counts/reasons and record concrete evidence read.
- Decide whether further investigation is needed and what questions remain.
- Authorize only truthful transitions later, with actual timestamps and evidence;
  acknowledgment is not an investigation, closure or forecasting approval.
- Keep disabled schedules, delivery, alarm actions and private publication status
  unchanged until separately reviewed. No independent-login requirement is invented.

Current packet disposition: **prepared; not acknowledged, investigated or closed
by Hampton**. Historical availability remains unknown; retrospective/unapproved
status flags are unchanged. This packet is decision support, not a human-review
attestation or a substitute for pending measurements.
