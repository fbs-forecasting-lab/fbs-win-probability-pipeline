# Final documentation source draft — unfinished release candidate

Prepared November 21, 2026. This is source for the December 1 PDF, not the final PDF or a claim that every requirement is complete. SageMaker/EC2 training compliance, genuine alert review, publication and final release verification remain open; see [readiness checklist](final-readiness.md).

## README core (target one-half to one page)

FBS Win Probability Pipeline is a UNC Charlotte DTSC 3601/3602 project estimating the designated home team's win probability for FBS football. It preserves versioned API captures and SHA-256 receipts in private S3, normalizes/excludes invalid games, constructs prior-season features, and fits a standardized logistic regression on 2022–2024 with an untouched 2025 holdout. Binary classification produces P(home wins), with the away probability equal to one minus it.

Confirmed team members are Hampton Abbott, Dharm Patel, Josh Livengood and Sarah Asianut Okwalinga. These names come from submitted team documents; individual implementation assignments are not verified and are not invented. Contact Hampton Abbott at [habbott1@charlotte.edu](mailto:habbott1@charlotte.edu).

Install Python 3.14.x, clone [the repository](https://github.com/fbs-forecasting-lab/fbs-win-probability-pipeline), create `.venv`, and install `requirements.txt`. Main's offline example is available today; the PM-02–PM-08 cloud work is on the release-candidate branch until reviewed integration. Preview it with `git fetch origin feature/final-readiness` then `git switch --track origin/feature/final-readiness` in a fresh clone.

```bash
git clone https://github.com/fbs-forecasting-lab/fbs-win-probability-pipeline.git
cd fbs-win-probability-pipeline
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -B bin/synthetic_demo.py --run-dir data/processed/synthetic-demo --allow-retrospective-demo
```

The entirely fictional example needs no cloud credentials or private data: 36 games yield 18 train, six holdout and six saved prediction rows. Outputs include dataset/model integrity reports, both evaluation baselines and reloaded probabilities. Use a fresh ignored directory; reruns refuse overwrite. Synthetic metrics test mechanics, not football skill. Windows uses `py -3.14` and `.venv\Scripts\python.exe`.

The authenticated cloud path additionally verifies ingestion, Athena/Python parity, Lambda training/inference, weekly scoring, private monitoring/review, an extractive Bedrock explanation and a five-game sportsbook comparison. It is not an approved live forecasting system. Historical availability is unknown, outcomes/rolling performance remain pending, recurrence/delivery are disabled, and all retrospective/unapproved flags remain unchanged. Local notebooks are an optional historical demo, not the final cloud compute path.

## License statement and complete copy

Original project code/documentation use MIT; third-party data, provider responses and restricted course/reference material are not licensed or redistributed by this grant.

```text
MIT License

Copyright (c) 2026 Hampton Abbott and the FBS Forecasting Lab project contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Classes and major functions (target one-half to one page, plus reference appendix)

The complete class inventory and actual docstrings are in [class-reference.md](class-reference.md), to include as a compact appendix during PDF assembly. Data classes `GamesResponse`, `Snapshot`, `SeasonInput` and `OddsResponse` bind exact bytes or normalized rows to source metadata. `S3Store` handles private verified transfers; `CloudS3Store`, `PreparationStore`, `ModelingStore`, `WeeklyStore`, `MonitorStore` and `InsightsStore` confine domain reads/writes and immutable receipts. Typed errors terminate invalid operations; `StepFailed` stops dependent notebook cells. Several hashed cloud classes/functions lack inline docstrings; external contracts document them without invalidating deployed identities. This is a remaining source-documentation quality gap, not silently marked complete.

`cfbd.fetch_games` and `storage.save_snapshot` preserve API captures. `games.load_snapshot`/`normalize_snapshot` validate hashes, schemas and FBS eligibility. `dataset.build_dataset` constructs Y-1 win-rate/margin differences and home-field status; final scores are labels only. `baseline.load_dataset`, `train_baseline`, `load_trusted_model` and `predict.predict_saved_sample` enforce split/hash/model contracts. `evaluate_probabilities` reports Brier, log loss, accuracy and descriptive calibration. Actual cloud handlers orchestrate these functions; [major-functions.md](major-functions.md) supplies signatures and failure conditions. Proposed SageMaker `managed_training.run` reuses the same baseline, and `public_monitoring.build_view` prepares only allowlisted dated scalars without publishing.

## Step-by-step use and troubleshooting

1. Run the synthetic quickstart, inspect `synthetic_summary.json`, then `model/evaluation.json` and `predictions/predictions.csv`. Confirm complementary finite probabilities and the synthetic notice. The same directory must fail on rerun without changing evidence.
2. For a new approved cloud training run, first verify the pinned preparation receipt and six S3 files. Use the [existing modeling runbook](cloud-modeling-runbook.md) for the verified Lambda behavior. Its prior invocation allowance is exhausted; do not rerun its commands without a new approval. A request supplied to `aws lambda invoke --invocation-type RequestResponse --payload file://<reviewed-request.json>` initiates computation in AWS, never on the laptop.
3. The required SageMaker alternative is **not yet cloud verified**. The [release proposal](release-proposal.md) describes a one-job File-channel candidate reusing the same baseline. PM-09A verified the digest-pinned Linux container synthetically; CPU quota/access and genuine job verification remain open before compliance closure. Do not call Lambda training SageMaker training or replace the protected model automatically.
4. Independent inference pins the trainer claim/completion and all nine model artifacts before trusted deserialization. Use the modeling runbook's saved-sample or hypothetical request; any new invocation needs approval. Saved outputs can be inspected without executing a model. Invalid feature domains and receipt hashes must stop before prediction/deserialization, respectively.
5. Monitoring consumes explicit verified predictions and separately selected later outcomes. Inspect sample sizes/coverage and pending/insufficient states before interpreting performance. Drift warnings request investigation, not automatic retraining. Use the [monitoring runbook](cloud-monitoring-runbook.md); review only an actual alert with truthful evidence, never claim the simulated smoke was a person's investigation.
6. On hash mismatch, ambiguous invocation, source/cutoff conflict or access denial, stop and preserve the original evidence. Do not retry a fresh token, refetch, weaken eligibility or expand permissions. Expired fixed schedule inputs cannot become recurring operation by enabling a switch. Secrets stay off screen/out of Git; no old workload allowances remain.

## Evidence, interpretation and limitations

Historical AWS training used 2,194 train and 740 holdout rows. Model Brier/log loss/accuracy were 0.21061287148858282 / 0.6096025525960278 / 0.6648648648648648; the training-rate constant baseline was 0.24163577488303326 / 0.6763272181260667 / 0.5918918918918918. Ten fixed calibration bins are descriptive, not an extra fitted calibration model. These are historical holdout results, not rolling/prospective performance.

The standardized margin coefficient was 0.7902: a plausible conditional signal of team strength. Win-rate difference was -0.0362, small and conditional on correlated margin; do not interpret that sign as winning being harmful. Home field was 0.0660, a small venue association. These are associations, not causal effects or independent feature-importance rankings. Prior-season summaries omit current-season roster/form/injury/weather changes.

The genuine LLM call used 257 input/42 output tokens to select seven verified fact sentences. Its narrow usefulness is stakeholder presentation under exact factual constraints; it does not calculate authoritative metrics or produce unrestricted analysis. Invalid output and provider failure remain unavailable, with offline failure tests rather than invented live failure observations. The odds comparison aligned five of 53 rows, with no outcomes or outperformance claim. Detailed individual comparison rows remain private. Distribution warnings do not establish concept drift; all genuine alerts still require truthful review.

## Source references and final assembly

Authority: DTSC 3602 syllabus pp.2,5–6; Final Documentation p.1; Final Demo Presentation p.1; newest instructor announcement as forwarded in PM-01; team Workplan pp.1–2, Initial Documentation pp.1–2 and Market Research pp.1–2. Primary course files stay private; see [final-readiness.md](final-readiness.md) for exact titles, scope and unavailable original announcement. The submitted market research cites South & Egros (2020), DOI 10.3233/JSA-190314, and Coleman (2025), DOI 10.1177/22150218251365223; these provide background, not evidence that this implementation matches their performance. The papers and final bibliography balance still need final source verification.

Implementation evidence: [ingestion](cloud-ingestion-verification.md), [preparation](cloud-preparation-verification.md), [modeling](cloud-modeling-verification.md), [weekly](weekly-cloud-verification.md), [monitoring](cloud-monitoring-verification.md), [explanation](cloud-stakeholder-verification.md) and [market](sportsbook-verification.md) records. Service contracts are linked in their runbooks. No cloud demonstration was repeated for this draft.

Final assembly must preserve every required component, not delete the full license or class/tutorial content to force an exact page count. The assignment says approximately two pages; aim for concise README and class/function summaries, then a compact license/tutorial/reference appendix if necessary. PDF rendering, link checks and final length/layout review remain pending. Final PDF/code are due **December 1, 2026 at 10 a.m. Eastern**; PPTX is due **9 a.m.**, with a five-minute hard stop plus one-minute questions.
