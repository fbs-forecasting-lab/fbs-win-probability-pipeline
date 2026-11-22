# Final demonstration outline — five-minute hard stop

Source: Final Demo Presentation p.1. PPTX due December 1, 2026 at 9 a.m. Eastern;
attendance required, presentation order randomized; one additional minute Q&A.
This is an outline, not slides or a rehearsed final presentation. Resolve the
[readiness gaps](final-readiness.md) before claiming the final system is complete.

| Time | Material / rubric coverage | Evidence and boundary |
| --- | --- | --- |
| 0:00–0:40 | Stakeholders and need: understandable FBS win probabilities; fans/analysts/data engineers | Submitted stakeholder statement; no betting-profit claim |
| 0:40–1:10 | Market research and contribution: reproducible cloud lifecycle, monitoring, timestamped benchmark | Submitted research pp.1–2; do not claim superiority over literature |
| 1:10–2:15 | Method: API → private S3 receipts → normalization → Athena/Python parity → chronological features → training | Architecture and PM-02/03 records; [PM-13B](managed-training-verification.md): actual SageMaker job Completed, 2,194/740/59 rows, 53 training/billable seconds; show PM-13D independent reload and disclose the fit-count corroboration gap |
| 2:15–3:15 | Output/evaluation: held-out comparison, calibration and model interpretation; independent API reload | PM-13B measured metrics match historical PM-04; three features and pinned inputs. PM-04 API reload is historical; new native reload remains blocked |
| 3:15–4:15 | Monitoring/explanation/market: pending labels, warnings, constrained factual summary, five/53 overlap | PM-06/07 evidence and [published saved scalar view](monitoring-publication-review.md); distinguish dated demonstration from current health, simulations from genuine review |
| 4:15–4:45 | Limitations: unknown historical availability, pending outcomes, limited coverage, prior-season-only features and disabled recurrence | Keep every retrospective/unapproved flag; no operational forecast claim |
| 4:45–5:00 | Conclusion: what was verified, release state and next evidence needed | Explicitly name any remaining compliance gap; stop at 5:00 |

Use large readable text and one clear architecture image/table per slide where
useful. A live demo or video is optional, not mandatory. Prefer preserved verified
AWS screenshots/receipts with private identifiers hidden; do not spend another
provider/training allowance for presentation polish. A local controller may
observe/initiate only newly approved cloud work, not perform graded computation
locally. The offline synthetic example is reviewer onboarding, not cloud proof.

Before the final PPTX: choose approved evidence, confirm every rubric item appears,
confirm all contributors without inventing roles, rehearse to 4:45–5:00, test the
presentation computer and fallback video/images, verify links/access, and submit
the PPTX actually used in class. Do not expose credentials, full resource names,
raw data or private stakeholder artifacts. Reserve the question minute for named
service compliance, leakage limitations and pending market outcomes.

Use saved PM-13B training evidence and the [PM-13D inference results](managed-training-verification.md). Show the independent 59-row byte match, the hypothetical home/away probabilities (66.24% / 33.76%) and the rejected receipt pin. Label the examples retrospective and approval withheld. One fit-attempt/completion record exists, with no training log stream to independently corroborate the exact total.
