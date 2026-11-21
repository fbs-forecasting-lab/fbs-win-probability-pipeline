# Saved monitoring publication - verification and review history

## PM-11 publication completed - November 21, 2026

The **static saved demonstration** is now public at:
[https://fbs-forecasting-lab.github.io/fbs-win-probability-pipeline/public-monitoring/](https://fbs-forecasting-lab.github.io/fbs-win-probability-pipeline/public-monitoring/)

- Publication branch/commit: `gh-pages`,
  [`212a659ceda0a04b76d8917f6435bb0045d7ccb6`](https://github.com/fbs-forecasting-lab/fbs-win-probability-pipeline/commit/212a659ceda0a04b76d8917f6435bb0045d7ccb6).
- Exact published HTML SHA-256: `cd128621a8e5ca88b6ab1dac727546549b8845cf7cedca0efe5fda42f710d975`.
- The isolated root commit contains only `public-monitoring/index.html` and an
  empty `.nojekyll`, with no parent history, workflow, docs folder or private data.
- Before publishing, Pages was absent (`has_pages=false`, GET 404 under admin
  access) and the publication branch was absent. On the authorized first branch
  push, GitHub automatically enabled legacy branch-root Pages from `gh-pages` `/`.
  A conservative guard stopped before an explicit create request; read-only
  verification confirmed the exact authorized configuration and resulting build
  commit. No configuration was replaced, explicit Pages POST/PUT was sent, or
  additional build trigger was issued. The first build observation was `built`.
- Unauthenticated HTTPS returned **200** at the exact URL; downloaded bytes and
  SHA-256 equaled the candidate. Fresh unauthenticated desktop (1280px) and narrow
  (375px) browser checks each returned the same matching HTML with no horizontal
  overflow, script/form/external asset tags or external asset requests. Both
  rendered screenshots were visually inspected.
- Privacy/content/attribution checks passed. Main, deployed renderers/producers,
  PM-09A bindings, source measurements, S3 settings and review states are unchanged.
  Unchanged application tests were not rerun.

The only authorized HTML changes from the reviewed PM-10 hash
`c17f2a45e62945ca7011e81b574b073e10e2f57b78142610eaa14a2f02e7f0ad`
were saved-demonstration labels/title/footer, quarantine 10/65 (15.38%) with TBD
times and warning above 10%, win-rate PSI 0.253 with warning above 0.20 and
2,194/53 reference/comparison rows, and the investigation-only explanation.
CSS, fixed date, 53 pending labels, unavailable rolling metrics and every
retrospective/unapproved safeguard were preserved. No measurements were refreshed.

**Only the static public-view portion is complete.** This is not a current health
feed, reviewed incident disposition, live forecast or operational approval.
Recurrence, delivery, pending outcomes, genuine review and SageMaker/EC2 execution
remain separate gaps. No paid activation, AWS change, workload, provider request,
query, schedule activation or monitoring-review transition occurred.

Rollback remains available: disable only this newly created Pages site, preserve
branches/history/evidence, and verify unavailability after cache propagation.
No rollback was necessary or executed. Detailed responses/screenshots and exact
source bindings remain in ignored `data/processed/pm11-publication-20261121T163859Z/`.

## Historical PM-10 preparation (superseded by the authorized PM-11 result above)

**The following records the pre-publication proposal and its original content hash.**
The review source is [monitoring-review.html](monitoring-review.html). It is a
presentation-only candidate based on the previously sanitized saved view. The
original PM-08 HTML/source binding is preserved unchanged; no producer renderer,
raw report, inference result or operational status was modified.

## Content and evidence binding

- Saved report as-of: **2026-11-20T22:30:00Z** (November 20, 5:30 p.m. Eastern).
- Counts: 65 raw, 55 retained, 10 quarantined, 53 technical rows and 53 pending
  labels, zero matched labels. Rolling losses/accuracy/calibration unavailable.
- Every retrospective/unapproved flag remains; operational approval is withheld.
  Saved source age is explicitly age at the report boundary, not current health.
- Only aggregate counts/states and explanatory presentation text. No raw rows,
  teams/predictions, resource identities, keys, review text, source/model IDs,
  analytics, JavaScript, forms or external assets.
- Exact candidate HTML SHA-256: `c17f2a45e62945ca7011e81b574b073e10e2f57b78142610eaa14a2f02e7f0ad`.
- Original preserved HTML SHA-256:
  `cbacf808add729f70b4f4d2e2ebdc8cbef8bea613b33483a7384896c5ac8d677`.
- Candidate and original were rendered at 1280-pixel desktop and 375-pixel
  narrow widths. Local screenshots/layout evidence remain ignored. No claim
  of public browser availability is made.

## Historical PM-10 hosting check - read-only

GitHub repository metadata reports public visibility, default branch `main`,
`has_pages=false`, and admin access for the authenticated account. GET `/pages`
returned 404. Together these establish **no Pages site configured at the check**,
not simply an anonymous permission failure. The proposed `gh-pages` branch was
also absent in a read-only remote-reference check. No Pages POST/PUT/DELETE,
build trigger, repository-setting change or publication branch creation ran.

## Historical proposed method - approved within PM-11

1. Recheck Pages settings/branch absence and the exact approved HTML hash. Stop
   for an existing/new configuration or content drift; do not replace another site.
2. With explicit publication approval, create a dedicated `gh-pages` branch from
   an isolated publication tree containing **only** `public-monitoring/index.html`
   (the byte-identical approved candidate) and an empty `.nojekyll` file. Do not
   publish the entire docs folder or raw/private evidence. Do not change main.
3. Configure Pages **Deploy from a branch: gh-pages / (root)**. This deliberately
   replaces the older main/docs suggestion with an isolated, minimal site. Allow
   the resulting Pages build only under that publication approval; add no workflow,
   scheduled action, cloud service, notification, subscription or public bucket.
4. Proposed URL:
   [https://fbs-forecasting-lab.github.io/fbs-win-probability-pipeline/public-monitoring/](https://fbs-forecasting-lab.github.io/fbs-win-probability-pipeline/public-monitoring/).
   This is a proposal, not a currently verified endpoint.
5. After an approved publish, check unauthenticated HTTPS access, download/hash
   equality of the HTML, no excluded content, labels/date/Unavailable values,
   desktop/narrow rendering and absence of external requests. Preserve reviewed
   content/site settings evidence. Publication does not confer forecast approval.

## Rollback - proposed, not executed

For an accidental disclosure or wrong deployment, first disable the newly created
Pages site through repository Pages settings (the equivalent is DELETE `/repos/`
`fbs-forecasting-lab/fbs-win-probability-pipeline/pages`). This restores the
previously observed no-site state; preserve the branch, commits and all evidence.
Verify the public URL is no longer serving content, allowing for cache propagation.
Do not rewrite Git history, delete private data or change S3 access. A later
correction requires a new reviewed HTML hash, ordinary commit and separately
approved re-publication. Do not force-push or automatically enable hosting again.

The approval must cover the exact HTML hash, the isolated branch/tree, Pages
configuration/build, read-only public verification and emergency disable rollback.
No execution approval is requested or implied by this preparation.

Official method contracts checked during preparation:
[branch publishing source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
and [Pages REST settings/disable operations](https://docs.github.com/en/rest/pages/pages).
GitHub documents branch-root publication and Pages availability for public Free
repositories; this proposal creates no paid hosting subscription. Actual hosting
settings were read separately as described above, without invoking a build.
