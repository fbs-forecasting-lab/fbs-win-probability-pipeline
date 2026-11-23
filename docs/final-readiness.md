# PM-08 final requirements and release readiness

## Current submission checklist

| Basis | Status | Evidence and remaining dependency |
|---|---|---|
| Professor — managed training and API inference | verified complete | [Measured results](managed-training-verification.md). Missing logs limit only independent fit-count corroboration. |
| Professor — documentation and shared code | partially complete | [Candidate source](final-documentation-review.md) and [inline inventory](inline-docstring-review.md). Team must approve and submit the PDF and repository link. |
| Professor — presentation | needs verification | [Demo outline](final-demo-outline.md). Team must rehearse, check the PPTX and submit it. |
| Professor — end-to-end cloud demonstration | needs verification | [Demo outline](final-demo-outline.md). Review the saved cloud evidence in the final presentation and distinguish the offline tutorial from graded execution. |
| Professor — human-or-LLM monitoring review | verified complete | [Supplied review of November 20](week13-monitoring-review.md) assessed reported measurements. The distribution-shift cause and Week 13 performance remained unresolved. |
| Project commitment — genuine incident investigation | missing | [Review packet](monitoring-review-packet.md). A team member must supply actual findings. |
| Project commitment — recurring scoring and delivery | partially complete | [Release proposal](release-proposal.md). Saved processing and display are verified. Recurrence and delivery remain disabled pending authorization. |
| Project commitment — outcome-based monitoring and market comparison | partially complete | [Saved monitoring evidence](monitoring-publication-review.md). Paired outcomes are required for performance evaluation. See the [Week 13 pregame and evaluation protocol](week13-update.md). |
| Optional — additional model features | missing | [Release scope](release-proposal.md). Outside this submission. |

Milestone statements below document the state on their recorded dates. This checklist supersedes earlier status claims.

As of November 22, 2026. **Not a declaration of requirement-complete release.**
All earlier deliverables and peer reviews are complete by Hampton's confirmation;
submission receipts are not requested and that coursework is not reopened.

## Authority and source availability

The local course files were read page-by-page with PDFKit text extraction. They
remain private; this checklist paraphrases their requirements rather than
redistributing them.

| ID | Authority / exact source | Relevant scope |
| --- | --- | --- |
| S | `DTSC 3602/Course_Admin/DTSC 3602 Syllabus-1.pdf`, pp.2,5–6 | Full serverless pipeline; API/S3/query/aggregation; LLM application; SageMaker or EC2 training; interpretation/evaluation/review; deployable code; sources and peer audience |
| A | Newest instructor announcement forwarded in PM-01, lines 25–33 of its supplied request | Cloud execution; a local notebook/script may control cloud work; deductions for local data uploads/training/execution. Original announcement export/date is unavailable in the supplied course directories. The forwarding is evidence of the instruction, not an invented Lambda exemption. |
| D | `DTSC 3602/Project/9. Final Documentation.pdf`, p.1 | PDF README/install/use/contributors, license statement/full copy, classes and major helpers/docstrings, tutorial examples and commented code; approximate length guidance |
| P | `DTSC 3602/Project/8. Final Demo Presentation.pdf`, p.1 | PPTX due December 1, 9 a.m. ET; attendance; five-minute hard stop plus one-minute questions; stakeholders, research, method/reproducibility, limitations, conclusion |
| W | `DTSC 3601/Project/FBS Win Probability Pipeline - Workplan.pdf`, pp.1–2 | Weekly FBS probabilities, minimum viable pipeline first, candidate features and scope/cost/leakage risks |
| I | `DTSC 3601/Project/FBS Win Probability Pipeline - Initial Documentation.pdf`, pp.1–2 | MIT, conceptual interfaces, timestamp controls, examples/monitoring intent; interfaces may evolve |
| M | `DTSC 3601/Project/FBS Win Probability Pipeline - Market Research.pdf`, pp.1–2 | Architectural contribution, recurring weekly operation, public monitoring dashboard and sportsbook benchmark commitments |
| R | `DTSC 3602/Project/Group 1 Reviews.pdf`, p.1 | Advisory received suggestions; syllabus p.5 requires incorporation or reasoned response, not universal adoption |

Course paths above are beneath Hampton's local `Documents/UNCC/Fall 2026/`.
Primary text extractions/hashes are private readiness evidence. No separate
newer announcement was found; none is fabricated. Lecture examples (Docker,
Kubernetes, API Gateway, every database) are not automatically extra requirements.

## Sourced checklist

Statuses: **verified complete**, **partially complete**, **missing**, **needs verification**.
Prior cloud evidence below is historical PM-02–PM-07 evidence, not new workloads.

| Item / authority | Status | Evidence | Remaining work / dependencies |
| --- | --- | --- | --- |
| Earlier deliverables and peer reviews — user confirmation | verified complete | Confirmed by Hampton | None; no receipt audit |
| API capture and private S3 — S p.5, A | verified complete | [PM-02C](cloud-ingestion-verification.md), [PM-07C](sportsbook-verification.md) | Preserve lineage/secret privacy; old allowances exhausted |
| Athena or Redshift; joins/aggregation — S p.5 | verified complete | [PM-03D](cloud-preparation-verification.md): actual Athena results passed Python parity | Redshift is an alternative, not another required service; current preparation is recovery-only |
| Train on SageMaker or EC2 — S p.5 | complete — actual named-service training verified | [PM-13B](managed-training-verification.md): original real-data SageMaker job Completed; seven artifacts, 2,194/740/59 counts and measured holdout/calibration verified | Full PM-13 acceptance remains incomplete: exact service fit-count corroboration unavailable; independent inference is verified separately below |
| Managed-model private receipt and independent native API checks — PM-13 acceptance | verified complete | [PM-13D verification](managed-training-verification.md) records immutable receipt read-back, complete 59-row equality, complementary hypothetical probabilities and invalid-pin rejection across three AWS calls | Historical availability and operational approval remain unverified. Independent training fit-count corroboration remains unavailable. |
| Fully cloud/serverless processing — S p.2, A | partially complete | Cloud ingestion/preparation/training/scoring verified; local notebook is optional historical path | Final graded controller/demo and named-service training closure; don't present local synthetic training as cloud execution |
| Model execution through APIs — S p.2 | verified complete | PM-04C independently invoked private inference, integrity refusals | Public inference endpoint not explicitly required; future SageMaker-artifact promotion must preserve trusted reload if used in final API demo |
| LLM API application and usefulness/failure assessment — S pp.2,5 | verified complete for bounded scope | [PM-07A](cloud-stakeholder-verification.md): genuine 257/42-token extractive summary, factual validation, offline failure tests | Final narrative distinguishes narrow extractive usefulness from unrestricted generation; failure tests are not invented provider incidents |
| Feature interpretation — S p.5 | verified complete for baseline | PM-04 coefficients/scales and [draft](final-documentation-draft.md) domain hypotheses | Explain conditional/correlated/noncausal signs, not standalone rankings |
| Input/distribution monitoring — S p.5 | verified complete for saved observations | [PM-06C](cloud-monitoring-verification.md): quality and distribution warnings with sample sizes | No claim that a drift indicator proves concept drift or authorizes retraining |
| Rolling performance monitoring — S p.5, I/M | partially complete | Implemented chronological outcome join/coverage gates, offline tests; 53 saved labels pending | Genuine later outcomes/coverage and measured windows require a new bounded capture proposal; never fill missing metrics with zero |
| Human or LLM review of model health — S p.5 | partially complete | Genuine report and constrained LLM facts exist; [PM-10 review packet](monitoring-review-packet.md) prepared; only simulated alert has recorded review transitions | Hampton must actually review findings; this packet is not an acknowledgment/investigation/closure. No independent-login requirement is invented |
| Weekly automatic execution — W/M | partially complete | [PM-05C](weekly-cloud-verification.md), PM-07C manual bounded orchestration | Fixed schedule tokens/cutoff are unsuitable for recurring weeks; retain disabled until a fresh-request planner, time guard, budgets and safe replay are reviewed |
| Failure detection and external alert delivery — S p.5 / M | partially complete | Application-failure inspection and error alarm verified; rule/actions disabled | Detection works; automatic delivery/notification is unverified. No evidence all lecture notification examples are mandatory. No activation in PM-08 |
| Static public saved monitoring view — M p.2 | verified complete | [PM-11 publication](https://fbs-forecasting-lab.github.io/fbs-win-probability-pipeline/public-monitoring/): exact hash, unauthenticated HTTPS and desktop/narrow verification; [record](monitoring-publication-review.md) | Saved demonstration only. Recurrence, delivery, pending outcomes and operational approval remain separate gaps; no S3 access change |
| Sportsbook benchmark — M/I | verified complete for probability comparison; partially complete for outcome evaluation | PM-07C: one credit, five/53 aligned games, immutable replay | Limited coverage; later outcomes/paired performance remain deferred; no superiority claim |
| Point-in-time operational forecasts — W/I/M | partially complete | Cutoff/source/hash safeguards verified; unknown publication times remain flagged | Historical publication/revision evidence and operational approval remain unresolved; all false/retrospective flags persist |
| README/install/contact/license/examples — D p.1, S p.5 | verified complete for offline reviewer path | Fresh Python 3.14 installation and isolated synthetic quickstart; MIT/full copy; human team/contact | Recheck candidate/main instructions after approved integration |
| Classes/major functions/docstrings — D p.1 | partially complete | [class inventory](class-reference.md), [major functions](major-functions.md), four-page review PDF source with actual docstring excerpts | [PM-10 inventory](inline-docstring-review.md): four classes and 127 functions/methods lack inline docstrings; a coordinated provenance-compatible documentation patch remains |
| Deployable final code on main — S p.5, D | needs verification | All PM-02–PM-07 commits are ancestors of this candidate | Main remains at `b524cf0`; normal reviewed integration, no PR/merge in PM-08 |
| Final documentation PDF — D p.1 | partially complete | [Four-page REVIEW DRAFT source](final-documentation-review.md), full MIT/license and 22 classes; every page visually inspected; [build guide](final-review-build.md) | Content/remaining gaps, bibliography balance and final submission approval remain; this is not final publication. Due December 1 **10 a.m. ET** |
| Final PPTX/demo — P p.1 | missing final artifact | [five-minute outline](final-demo-outline.md) | Readiness closure, slide production/rehearsal and attendance; PPTX due December 1 **9 a.m. ET**; one minute Q&A |

## Received suggestion disposition (R p.1; advisory)

| Suggestion | Disposition and rationale |
| --- | --- |
| Replace assertions with explicit validation | Acknowledge one accounting invariant at `dataset.py:329`. Defer this source-byte change from the verified producer: ordinary validation already uses explicit errors, while changing this serialized producer requires compatibility records/repackaging across dependent cloud identities. Do not claim it was replaced. Include explicit error handling in the next coordinated producer release. |
| Configurable train/holdout/prediction seasons | Defer. Fixed chronology/model contracts preserve verified evidence; generalization requires versioned sources, tests and operational policy, not a few CLI flags. |
| Automated drift monitoring | Incorporated as quality/distribution/performance adapters, immutable alerts and review. Disclose disabled recurrence and pending real-label performance/review rather than claiming continuous automation. |
| In-season/additional predictors (repeated suggestions) | Defer until observation/publication timing and chronological evaluation can support them; prior-season-only limitation is explicit. Weather and every candidate feature are not compulsory implementations. |
| Multi-season cross-validation | Defer rolling-origin validation to a future modeling study; do not substitute random folds or tune on the untouched holdout. Current held-out comparison is not proof of cross-season robustness. |
| Random Forest / Gradient Boosting comparison | Defer. Neither rubric mandates a model tournament. Baseline plus training-rate comparison is reproducible; no optimality claim is made. |

## Current-round checks versus historical evidence

New: 342 offline tests passed (six new readiness tests); Python 3.14.2 fresh
installation; `pip check`; exact offline quickstart from a clean tracked-base
copy plus candidate additions with empty home/no private environment or AWS
configuration and blocked sockets; 18/6/6 counts; repeat exit 1 preserved 48
artifact bytes/mtimes. New local managed training matched synthetic evaluation;
static-view privacy/failed-state tests passed. No production fit/model/API call
occurred. Historical PM-04 metrics/PM-06 observations/PM-07 usage are labeled in
their dated records and were not re-executed.

Read-only SageMaker metadata is accessible under Free/Active with credits.
`ml.m5.large`, `ml.m5.xlarge` and `ml.c5.xlarge` training quotas are zero;
`ml.g5.xlarge`/`ml.g6.xlarge` quotas are one. Quota metadata is not proof of job
capacity, eligible GPU coverage or runtime success. No job, quota request,
upgrade or new cloud resource was initiated. The preferred small CPU candidate
is blocked; [the proposal](release-proposal.md) identifies the alternatives and
missing image/runtime evidence without inventing successful installation in Linux.

## PM-09A preparation update — newly executed November 21, 2026

[Managed-training readiness](managed-training-readiness.md) records the exact
current evidence and remaining decision. Existing OrbStack was started without
installation/configuration changes; a digest-pinned Linux x86_64 image passed
actual SageMaker-style launch/path/failure/SIGTERM checks on synthetic data.
All 23 new focused tests passed on host and in that image; the full blocked-network
suite passed **365 tests**. Native SageMaker provenance and independent reload are
verified only with explicitly synthetic service evidence; actual job-origin
verification and the syllabus's named-service execution remain missing.

Read-only metadata confirms FREE/ACTIVE, $119.99 credits and five zero CPU training
quotas. Existing bucket ownership/privacy/SSE-S3 and six-file input prefix are
unchanged. Six IAM documents validated without findings; 18 exact-context policy
simulations matched. None was attached. The smallest remaining access decision is
whether to authorize a quota-one `ml.m5.large` request/support inquiry while
retaining Free/zero personal payment; do not submit a job or upgrade. A separate
native inference bridge is proposed to preserve exact-version/producer checks.
PM-09B corrected the earlier runtime comparison: the receipt-verified cloud model
already uses Python 3.14.10; 3.14.2 was local-environment metadata. No previous
cloud workload, deployment, publication or activation was repeated.

## PM-09B access follow-up — newly executed November 21, 2026

Verified `sagemaker`, `us-east-1`, adjustable training quota `L-611FA074`,
`ml.m5.large for training job usage`, applied zero, with no equivalent pending,
open or approved request. Submitted the single authorized request for **one**.
Latest status: **CASE_OPENED** (awaiting AWS decision), applied quota still zero; account FREE/ACTIVE unchanged.
AWS opened a related case through the existing quota request; no separate
support inquiry or paid support/API activation occurred. Request/case
identifiers and detailed evidence stay ignored/private. Await the existing
request; do not duplicate it or treat quota approval as workload authorization.

Named-service execution remains **missing**, and the managed path remains blocked
on applied quota/access plus separate execution approval and real cloud-origin
verification. Documentation work verified research metadata/selected methods,
added a [reference audit](research-references.md), improved artifact/evaluation/
troubleshooting examples, and corrected the cloud/runtime comparison using
receipt-verified historical metadata. No deployed producer bytes, package, model,
application test or final published artifact changed; 365 passing tests remain
historical PM-09A evidence and were not rerun for these documentation edits.

## PM-10 independent review work — newly completed November 21, 2026

Started clean on `feature/final-readiness` at `547171d`; no earlier PM-10 source
or ignored preview was found. The actual Final Documentation instruction PDF was
read again: PDF, short README and class/function guide with docstrings, tutorials,
well-commented shared code, full license, no keys, approximately two pages. The
review keeps a two-page core plus required tutorial/license/docstring appendices
rather than deleting required content. All four rendered pages were inspected;
links/text/license/classes and output refusal were checked. Generated previews,
private source bindings and evidence remain ignored; reproducible sources are in Git.

| Scope / authority | Current disposition and dependency |
| --- | --- |
| Professor: named SageMaker/EC2 training; serverless execution — S/A | **Unchanged:** named-service execution remains missing. Hampton says professor email and existing AWS request have no response. No new access/workload call or exemption is claimed. Preserve PM-09A image/source/proposal bindings. |
| Professor: documentation, classes/docstrings, tutorial and code — D | REVIEW DRAFT prepared, not final. Inline omissions have an explicit source-byte compatibility plan; final bibliography/content and submission review remain. |
| Professor: monitoring/performance and human or LLM review — S | Existing technical evidence remains; genuine review packet is prepared only. Pending outcomes do not become measured performance. No human-review transition or personal attestation was created. |
| Submitted commitments: public monitoring, recurring weekly operation, market benchmark — W/M/I | Candidate static page is locally reviewed and hosting absence verified; publication awaits exact content/hosting approval. Schedules/delivery remain disabled, planner/cutoff/budgets unresolved. Market outcome evaluation still lacks paired outcomes. |
| Optional improvements: model alternatives, additional/in-season predictors, broader CV/configuration — R/W | Reasoned deferrals stand. No optional feature or service is added. Documentation improvements do not reopen completed coursework or peer reviews. |

Read-only GitHub settings: public repository, default main, admin visibility of
`has_pages=false` and Pages GET 404; proposed isolated publication branch absent.
[Publication proposal](monitoring-publication-review.md) pins the new review HTML
hash and proposes only `gh-pages` root with one HTML file and `.nojekyll`, replacing
the earlier main/docs suggestion. Nothing was hosted or activated. Desktop/narrow
checks covered original and candidate, preserved date/status and no external assets.

[Review packet](monitoring-review-packet.md): quarantine 10/65 (15.3846%, threshold
10%); win-rate feature PSI 0.2529945485983902 (threshold 0.20; 2,194 versus 53 rows);
zero matched/53 pending labels, null window metrics. Known facts, hypotheses,
unanswered questions and proportionate actions are separate. These are preserved
November 20 observations, not new PM-10 measurements or Hampton's review actions.

No application/deployed producer changed, no unchanged application suite was
rerun, and historical PM-09A tests remain labeled historical. No AWS workload,
provider request, quota duplicate, deployment, publication, hosting setting,
schedule, human-review transition, PR or merge occurred. Final PPTX production
and rehearsal remain later steps; earlier confirmed submissions remain complete.

## PM-11 saved monitoring demonstration - November 21, 2026

Published only the authorized static view at [https://fbs-forecasting-lab.github.io/fbs-win-probability-pipeline/public-monitoring/](https://fbs-forecasting-lab.github.io/fbs-win-probability-pipeline/public-monitoring/).
Publication commit: `212a659ceda0a04b76d8917f6435bb0045d7ccb6` on isolated `gh-pages`; exact HTML SHA-256:
`cd128621a8e5ca88b6ab1dac727546549b8845cf7cedca0efe5fda42f710d975`. The two-file root tree contains only the HTML and empty `.nojekyll`.
GitHub automatically configured the approved branch-root site on first push;
read-only verification accepted that exact state without replacing a configuration
or triggering another build. Build commit, unauthenticated HTTP 200, downloaded
hash, desktop/narrow layouts and absence of external assets were verified.

Added only saved warning facts (10/65 TBD kickoffs, 15.38%, above-10% trigger;
win-rate PSI 0.253, above-0.20 trigger, 2,194 training versus 53 scoring rows) and
saved-demonstration labels/interpretation. The fixed November 20 report boundary,
53 pending labels, unavailable metrics and all safeguards remain. No evidence
was refreshed, and no human review or operational approval is inferred.

Only static public-view delivery is complete. Disabled recurring scheduling,
automated alert/event delivery, later-outcome performance, genuine review,
SageMaker requirement/access and main integration remain unresolved as before.
No instructor/quotas response was inferred or duplicate request made. No
application test was rerun; verification was limited to actual content/hosting
changes. PM-09A image/source/request/proposal bindings and deployed producers
remain unchanged. See [publication verification](monitoring-publication-review.md).

## PM-13 authorized deployment attempt — November 21, 2026

[Actual verification](managed-training-verification.md): original executable and
private pins matched; current ml.m5.large training quota was 15; account remained
FREE/ACTIVE with $119.973485 estimated eligible credits covering all proposed
services. Six dataset files matched the preparation receipt. A network-disabled
Linux inspection verified the existing image's source/runtime without fitting.

One empty private repository, two scoped roles and two empty log groups were
created. ECR rejected the exact reviewed repository policy; deployment stopped
before image upload, SageMaker submission or bridge creation. **Zero jobs, fits
and inference calls** occurred; no new metrics/calibration or provenance receipt
exist. Original submission journal remains unconsumed. Predecessors, protected
model-object metadata, disabled rules, bucket protections, main and Pages remain
unchanged. Historical measurements remain separately labeled. The named-service
requirement remains missing, now blocked on repository-policy service acceptance
rather than the prior quota. No other requirement is marked complete.

## PM-13B managed-training execution — November 22, 2026

[Actual results](managed-training-verification.md): one equivalent-scope ECR
policy correction was accepted/read back; retained resources and original pins
were reconciled. One original submission completed in AWS Linux with 53 training/
billable seconds, 2,194 train / 740 holdout / 59 saved prediction rows and seven
verified artifacts. All six metrics equal historical Lambda results, with actual
calibration checked. FREE/ACTIVE eligible credits cover the retained resources.

Actual named-service training is now verified. **Full PM-13 acceptance is not**:
PAX timestamp headers block the unchanged native loader; no private native receipt,
bridge or inference calls occurred. One attempt/completion record and Training
phase are observed, but exact fit-count log corroboration is missing. No
application image, predecessor, input, bucket setting, main or Pages change was
made. No ambiguity was resolved by refitting or relaxing native validation.
379 network-blocked offline tests and four private controller tests passed.
