# Final documentation source draft — unfinished release candidate

Prepared November 21, 2026. This is source for the December 1 PDF, not the final PDF or a claim that every requirement is complete. SageMaker/EC2 training compliance, genuine alert review, publication and final release verification remain open; see [readiness checklist](final-readiness.md).

A [four-page REVIEW DRAFT](final-documentation-review.md) and [offline build/QA guide](final-review-build.md) now provide a compact two-page core plus required appendices. Generated PDFs remain ignored and are not final submissions. The [genuine monitoring-review packet](monitoring-review-packet.md) awaits actual review; it is not an attestation.

## README core (target one-half to one page)

FBS Win Probability Pipeline is a UNC Charlotte DTSC 3601/3602 project estimating the designated home team's win probability for FBS football. It preserves versioned API captures and SHA-256 receipts in private S3, normalizes/excludes invalid games, constructs prior-season features, and fits a standardized logistic regression on 2022–2024 with an untouched 2025 holdout. Binary classification produces P(home wins), with the away probability equal to one minus it.

Confirmed team members are Hampton Abbott, Dharm Patel, Josh Livengood and Sarah Asianut Okwalinga. These names come from submitted team documents; individual implementation assignments are not verified and are not invented. Contact Hampton Abbott at [habbott1@charlotte.edu](mailto:habbott1@charlotte.edu).

Install Python 3.14.x, clone [the repository](https://github.com/fbs-forecasting-lab/fbs-win-probability-pipeline), create `.venv`, and install `requirements.txt`. Main's offline example is available today; the PM-02–PM-09 readiness/cloud work is on the release-candidate branch until reviewed integration. Preview it with `git fetch origin feature/final-readiness` then `git switch --track origin/feature/final-readiness` in a fresh clone.

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

The following commands distinguish offline onboarding from separately authorized
cloud work. None of the cloud commands below was executed in PM-09B.

1. **Offline onboarding.** Run the README synthetic quickstart in a fresh ignored
   directory. Inspect `synthetic_summary.json`, `model/evaluation.json`,
   `model/calibration.json` and `predictions/predictions.csv`. Counts are 18/6/6;
   all teams and metrics are fictional. A rerun into the same directory must
   refuse overwrite. This does not demonstrate cloud training.
2. **Training source and consent.** Before any separately approved cloud run,
   verify the selected preparation completion receipt and all six dataset hashes.
   The verified Lambda trainer is documented in the [modeling runbook](cloud-modeling-runbook.md).
   Its old workload allowance is exhausted. The SageMaker path is a distinct,
   locally tested candidate in [managed readiness](managed-training-readiness.md).
   PM-09B's quota request is pending; even approval would not authorize a job.
3. **Cloud training after approval only.** Pin request/code/image/runtime and use
   the reviewed single-attempt controller. Fitting and evaluation run in AWS on
   2022–2024 training rows and the untouched 2025 holdout. Require actual successful
   completion, immutable artifacts, counts and measured metrics. Preserve failed
   or ambiguous evidence; never try a fresh name/token automatically.
4. **Independent saved-model inference after approval only.** The existing Lambda
   path verifies its producer claim/completion and nine artifacts before loading.
   The candidate SageMaker path verifies a native job/receipt/archive and seven
   baseline artifacts; its new bridge cannot accept a caller-selected model URL
   or caller-selected trust pin. Matching Python/library versions do not erase
   this producer distinction. Both paths reuse the existing trusted baseline
   loader and saved/vector prediction functions. Require saved CSV equality with
   the training sample and finite complementary hypothetical probabilities.
5. **Evaluate without another fit.** Inspect `evaluation.json` for model and
   training-rate constant baseline on exactly the same holdout games. Binary
   Brier score is mean squared probability error; log loss penalizes confident
   errors; lower is better for both. Accuracy uses the implemented 0.5 threshold
   and higher is better, but discards probability detail. `calibration.json` has
   ten fixed bins with sample counts and observed win rates; empty bins are
   unavailable, not zero. These bins are descriptive and do not fit a calibration
   model. The [reference notes](research-references.md) explain the scoring basis.
6. **Monitoring and stop conditions.** Pending labels mean rolling performance is
   unavailable; a distribution warning does not prove concept drift or authorize
   retraining. Review genuine findings truthfully, never present simulated smoke
   transitions as a person's investigation. On bad hashes, versions, access,
   cutoff/source conflicts or ambiguous responses, stop and preserve evidence.
   Do not loosen validation, enable expired schedule inputs or purchase access.

For a later approved private Lambda invocation, use the complete command form
below with only the reviewed function/request paths. It is a template, not a
currently executable request or a new allowance:

```bash
aws lambda invoke --region us-east-1 --invocation-type RequestResponse \
  --function-name "<reviewed-private-function>" \
  --cli-binary-format raw-in-base64-out \
  --payload "file://<reviewed-request.json>" \
  "<new-ignored-response.json>"
```

Inspect both the invocation envelope (`FunctionError`, when present) and the
application result's `state`/`stage`; a successful HTTP response alone is not
workflow completion. The expected negative-input FunctionError is meaningful
only within its approved test. Do not deserialize a downloaded `joblib` file on
the controlling laptop. Existing artifact JSON/CSV can be inspected without a fit
or model execution, for example after setting `REVIEW` to an existing trusted
local evidence directory:

```bash
.venv/bin/python -B -m json.tool "$REVIEW/evaluation.json"
.venv/bin/python -B -m json.tool "$REVIEW/calibration.json"
```

No command uses `latest`, prints credentials or creates a second training token.
Actual private locations/identities remain in reviewed ignored configuration.

## Evidence, interpretation and limitations

Historical AWS training used 2,194 train and 740 holdout rows. Model Brier/log loss/accuracy were 0.21061287148858282 / 0.6096025525960278 / 0.6648648648648648; the training-rate constant baseline was 0.24163577488303326 / 0.6763272181260667 / 0.5918918918918918. Ten fixed calibration bins are descriptive, not an extra fitted calibration model. These are historical holdout results, not rolling/prospective performance.

The standardized margin coefficient was 0.7902: a plausible conditional signal of team strength. Win-rate difference was -0.0362, small and conditional on correlated margin; do not interpret that sign as winning being harmful. Home field was 0.0660, a small venue association. These are associations, not causal effects or independent feature-importance rankings. Prior-season summaries omit current-season roster/form/injury/weather changes.

The genuine LLM call used 257 input/42 output tokens to select seven verified fact sentences. Its narrow usefulness is stakeholder presentation under exact factual constraints; it does not calculate authoritative metrics or produce unrestricted analysis. Invalid output and provider failure remain unavailable, with offline failure tests rather than invented live failure observations. The odds comparison aligned five of 53 rows, with no outcomes or outperformance claim. Detailed individual comparison rows remain private. Distribution warnings do not establish concept drift; all genuine alerts still require truthful review.

## Source references and final assembly

Authority: DTSC 3602 syllabus pp.2,5–6; Final Documentation p.1; Final Demo Presentation p.1; newest instructor announcement as forwarded in PM-01; team Workplan pp.1–2, Initial Documentation pp.1–2 and Market Research pp.1–2. Primary course files stay private; see [final-readiness.md](final-readiness.md) for exact titles, scope and unavailable original announcement. The submitted market research cites South & Egros (2020), DOI 10.3233/JSA-190314, and Coleman (2025), DOI 10.1177/22150218251365223; these provide background, not evidence that this implementation matches their performance. PM-09B checked publisher/author research metadata and selected methods in [research-references.md](research-references.md), with access/version limitations stated. The final assembled bibliography balance and formatting remain pending.

Implementation evidence: [ingestion](cloud-ingestion-verification.md), [preparation](cloud-preparation-verification.md), [modeling](cloud-modeling-verification.md), [weekly](weekly-cloud-verification.md), [monitoring](cloud-monitoring-verification.md), [explanation](cloud-stakeholder-verification.md) and [market](sportsbook-verification.md) records. Service contracts are linked in their runbooks. No cloud demonstration was repeated for this draft.

Final assembly must preserve every required component, not delete the full license or class/tutorial content to force an exact page count. The assignment says approximately two pages; aim for concise README and class/function summaries, then a compact license/tutorial/reference appendix if necessary. PDF rendering, link checks and final length/layout review remain pending. Final PDF/code are due **December 1, 2026 at 10 a.m. Eastern**; PPTX is due **9 a.m.**, with a five-minute hard stop plus one-minute questions.
