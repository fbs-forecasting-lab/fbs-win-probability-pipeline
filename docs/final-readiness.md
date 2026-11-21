# PM-08 final requirements and release readiness

As of November 21, 2026. **Not a declaration of requirement-complete release.**
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
| Train on SageMaker or EC2 — S p.5 | **missing** | [PM-04C](cloud-modeling-verification.md) proves Lambda training only | Actual named-service job remains missing. PM-09A Linux image/native lineage verified synthetically; CPU quota/access resolution and genuine cloud verification remain; no exemption established |
| Fully cloud/serverless processing — S p.2, A | partially complete | Cloud ingestion/preparation/training/scoring verified; local notebook is optional historical path | Final graded controller/demo and named-service training closure; don't present local synthetic training as cloud execution |
| Model execution through APIs — S p.2 | verified complete | PM-04C independently invoked private inference, integrity refusals | Public inference endpoint not explicitly required; future SageMaker-artifact promotion must preserve trusted reload if used in final API demo |
| LLM API application and usefulness/failure assessment — S pp.2,5 | verified complete for bounded scope | [PM-07A](cloud-stakeholder-verification.md): genuine 257/42-token extractive summary, factual validation, offline failure tests | Final narrative distinguishes narrow extractive usefulness from unrestricted generation; failure tests are not invented provider incidents |
| Feature interpretation — S p.5 | verified complete for baseline | PM-04 coefficients/scales and [draft](final-documentation-draft.md) domain hypotheses | Explain conditional/correlated/noncausal signs, not standalone rankings |
| Input/distribution monitoring — S p.5 | verified complete for saved observations | [PM-06C](cloud-monitoring-verification.md): quality and distribution warnings with sample sizes | No claim that a drift indicator proves concept drift or authorizes retraining |
| Rolling performance monitoring — S p.5, I/M | partially complete | Implemented chronological outcome join/coverage gates, offline tests; 53 saved labels pending | Genuine later outcomes/coverage and measured windows require a new bounded capture proposal; never fill missing metrics with zero |
| Human or LLM review of model health — S p.5 | partially complete | Genuine report and constrained LLM facts exist; only simulated alert has review transitions | Truthful review of genuine findings still needed; no independent human login/incident closure requirement is invented |
| Weekly automatic execution — W/M | partially complete | [PM-05C](weekly-cloud-verification.md), PM-07C manual bounded orchestration | Fixed schedule tokens/cutoff are unsuitable for recurring weeks; retain disabled until a fresh-request planner, time guard, budgets and safe replay are reviewed |
| Failure detection and external alert delivery — S p.5 / M | partially complete | Application-failure inspection and error alarm verified; rule/actions disabled | Detection works; automatic delivery/notification is unverified. No evidence all lecture notification examples are mandatory. No activation in PM-08 |
| Public monitoring dashboard — M p.2 | partially complete | New scalar-only static candidate with 53 pending labels, no private identities | User content approval, hosting/settings verification and publication approval; no bucket public-access changes |
| Sportsbook benchmark — M/I | verified complete for probability comparison; partially complete for outcome evaluation | PM-07C: one credit, five/53 aligned games, immutable replay | Limited coverage; later outcomes/paired performance remain deferred; no superiority claim |
| Point-in-time operational forecasts — W/I/M | partially complete | Cutoff/source/hash safeguards verified; unknown publication times remain flagged | Historical publication/revision evidence and operational approval remain unresolved; all false/retrospective flags persist |
| README/install/contact/license/examples — D p.1, S p.5 | verified complete for offline reviewer path | Fresh Python 3.14 installation and isolated synthetic quickstart; MIT/full copy; human team/contact | Recheck candidate/main instructions after approved integration |
| Classes/major functions/docstrings — D p.1 | partially complete | [class inventory](class-reference.md), [major functions](major-functions.md), actual docstring excerpts | Some hashed cloud classes/functions lack inline docstrings. External contracts close navigation gaps; inline changes need provenance compatibility/repackaging review |
| Deployable final code on main — S p.5, D | needs verification | All PM-02–PM-07 commits are ancestors of this candidate | Main remains at `b524cf0`; normal reviewed integration, no PR/merge in PM-08 |
| Final documentation PDF — D p.1 | partially complete | [unfinished source draft](final-documentation-draft.md) includes complete MIT text and tutorials | Resolve above gaps, class appendix, citations/bibliography balance (S p.6), typeset/render/check PDF; due December 1 **10 a.m. ET** |
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
