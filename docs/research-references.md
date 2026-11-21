# Final documentation reference notes — source work in progress

Checked November 21, 2026. These references support the design discussion; they
are not evidence that this project's implementation reproduces another paper's
results. No articles, provider datasets or restricted course PDFs are redistributed.
The final PDF bibliography and its peer-reviewed-source balance still require
assembly and review; do not count vendor documentation as peer-reviewed research.

## Football methods and evaluation

1. South, C., & Egros, E. (2020). Forecasting college football game outcomes using
   modern modeling techniques. *Journal of Sports Analytics, 6*(1), 25–33.
   [Publisher and DOI](https://journals.sagepub.com/doi/10.3233/JSA-190314).
   Publisher metadata confirms authors, title, year, issue and pages. The work
   studies several methods using 2011–2014 data and forecasts score differences.
   It motivates comparison and opponent/venue awareness; our three-feature binary
   probability baseline does not reproduce its features, tuning or study design.

2. Coleman, B. J. (2025). A predictive metamodel for college football.
   *Journal of Sports Analytics, 11*.
   [Publisher and DOI](https://journals.sagepub.com/doi/10.1177/22150218251365223).
   The publisher confirms the author, title, volume and July 30 online date;
   its PDF labels pages 1–7 without a finalized issue number. Do not invent one.
   The abstract/methods describe combining rating-system margin predictions and
   comparing them with betting lines. This motivates timestamp-aligned benchmark
   coverage, not a claim that our five paired moneyline comparisons establish
   predictive superiority or reproduce that margin-based experiment.

3. Gneiting, T., & Raftery, A. E. (2007). Strictly proper scoring rules,
   prediction, and estimation. *Journal of the American Statistical Association,
   102*(477), 359–378. DOI: 10.1198/016214506000001437.
   [Author-hosted published article](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf).
   The published text discusses probability scoring and comparing predictions
   on the same observations. It supports reporting probability-sensitive losses
   alongside threshold accuracy. Our code uses binary Brier score and log loss
   with lower being better; it does not implement every scoring rule in the paper.

## Reproducibility and software

4. Kapoor, S., & Narayanan, A. (2023). Leakage and the reproducibility crisis in
   machine-learning-based science. *Patterns, 4*(9), 100804.
   [Published DOI](https://doi.org/10.1016/j.patter.2023.100804).
   Publisher-indexed metadata confirms the published article. The final publisher
   page was inaccessible in this check; the [authors' 2022 preprint](https://arxiv.org/abs/2207.07048)
   was accessible. That preprint supports the general warning about leakage and
   overoptimistic comparisons; do not silently treat its version-specific results
   as a full-text verification of the final article. This project's chronological
   fitting and immutable records address some reproducibility risks but do not
   prove historical publication times or operational forecasting eligibility.

5. Pedregosa, F., et al. (2011). Scikit-learn: Machine Learning in Python.
   *Journal of Machine Learning Research, 12*(85), 2825–2830.
   [Journal article](https://jmlr.org/papers/v12/pedregosa11a.html).
   The journal page verifies authorship, bibliographic fields and the software
   abstract. Cite it for the library; inspect the actual version-pinned repository
   code for this project's estimator settings and serialization contract. The
   2011 article does not establish behavior of the installed 2026 release.

## Service contracts and scope of verification

- [SageMaker container launch](https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-training-algo-dockerfile.html)
  and [training output](https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-training-algo-output.html)
  define the launch/path/signal contract. PM-09A Linux checks are local synthetic
  evidence, not proof that a SageMaker job has executed.
- [Quota request API](https://docs.aws.amazon.com/servicequotas/2019-06-24/apireference/API_RequestServiceQuotaIncrease.html)
  distinguishes a submitted request from its resulting applied quota. It has no
  use-case text field; `SupportCaseAllowed` permits related case creation. A
  pending request is not an approval or workload authorization.
- [Basic account/billing support](https://docs.aws.amazon.com/awssupport/latest/user/case-example.html)
  differs from technical support. The [Support API](https://docs.aws.amazon.com/awssupport/latest/APIReference/API_CreateCase.html)
  requires specified paid support plans; do not subscribe merely to call it.
  PM-09B does not use that API or create a second inquiry while the quota route
  is pending.

Before final submission, reconcile every in-text citation with its reference,
verify any additional literature claims against the actual version consulted,
recount all research and technical sources against the syllabus guidance, and
keep course requirements distinct from research findings and historical project
verification. PDF formatting, accessibility and final bibliography review remain
unfinished. Bibliographic metadata/selected methods were checked; no experiment
from these papers was independently replicated.
