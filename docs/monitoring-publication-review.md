# Monitoring content review and proposed publication

**PM-10 proposal only - no hosting change or publication performed.**
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

## Existing hosting - newly checked read-only

GitHub repository metadata reports public visibility, default branch `main`,
`has_pages=false`, and admin access for the authenticated account. GET `/pages`
returned 404. Together these establish **no Pages site configured at the check**,
not simply an anonymous permission failure. The proposed `gh-pages` branch was
also absent in a read-only remote-reference check. No Pages POST/PUT/DELETE,
build trigger, repository-setting change or publication branch creation ran.

## Exact proposed method - requires separate approval

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
