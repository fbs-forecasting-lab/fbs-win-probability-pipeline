# PM-07B: genuine sportsbook comparison preparation

**PM-07C completed the bounded capture/comparison and replay procedure.** See the
[actual verification record](sportsbook-verification.md): five shared games,
pending labels and no performance claim. The allowances below are exhausted;
these commands describe the reviewed procedure, not permission to repeat it.
The verified PM-07A explanation is unchanged and its allowance is exhausted.
The current branch starts at `4f530430cb76a92cec7bff3f24c0ca28702cddcc`.

## One operator setup instruction

Obtain a **Starter FREE** key from [The Odds API](https://the-odds-api.com/) off
screen and confirm the account is free with at least **one unused credit**.
Do not purchase historical access or change an existing subscription. Never send
the key in chat; retain it for the separately approved hidden Terminal procedure.
This was the PM-07B prerequisite. PM-07C subsequently confirmed free access and
created `fbs/the-odds-api-key` through hidden Terminal input; its value was not
retrieved locally. It is now bound to the benchmark function only.

The advertised free plan has 500 monthly credits, all sports/markets and most
bookmakers, without historical odds. Account-specific quota and DraftKings
availability are unverified. AWS credits do not cover this third-party account.
The [v4 documentation](https://the-odds-api.com/liveapi/guides/v4/) identifies
`americanfootball_ncaaf` and current `/v4/sports/americanfootball_ncaaf/odds`.
One `regions=us&markets=h2h` request costs one quota unit; decimal formatting and
a date window do not add regions/markets. Preserve actual quota headers. Public
documentation is not an authenticated endpoint/account test. No sport-list or
other discovery request is proposed; missing bookmaker/markets remain gaps.

## Fixed candidate, supported by saved schedule evidence

Read-only inspection verified the saved cloud Week 13 source: **65 records**,
scheduled November 25 at 00:00 UTC through November 29 at 04:00 UTC. This is
schedule evidence for choosing season **2026 / week 13**, not a new capture or a
guarantee that quotes exist. Current preparation was November 21 UTC, November 20
Eastern time. A fresh source must still pass all existing eligibility checks.

- Cutoff: **2026-11-21T18:00:00Z**. Latest workflow start: **17:20 UTC** that day.
- Odds window: **2026-11-25T00:00:00Z–2026-11-30T00:00:00Z**; decimal US h2h.
- Bookmaker fixed in advance: **draftkings**, with no substitute or best-price selection.
- Weekly token/execution: `pm07b-week13-paired-20261121`.
- New ingestion token: `pm07b-week13-capture-20261121`.
- Market token: `pm07b-market-capture-20261121`.
- Benchmark token: `pm07b-compare-week13-20261121`.
- Completed weekly replay execution: `pm07b-week13-paired-replay-20261121`, using
  the identical original request/run token, not a new capture token.

Private exact requests, five verified historical source references, protected
model reference, prior Week 13 summary/revision reference, parameters and hashes
are in ignored `data/processed/pm07b-readiness-20261121/`. No historical backfill,
training or old-cutoff substitution is proposed. History and protected model
remain the PM-05/PM-04 identities. New preparation/scoring executes in the weekly
worker; the local controller only verifies evidence and creates explicit mappings.

## Secret/configuration scope, only after separate approval

1. Recheck Free/Active AWS credits and operator confirmation of free odds access.
   Stop if any upgrade, paid activation, subscription or personal payment is needed.
2. Run in a real off-screen Terminal from the repository, using the private
   proposal's expected account (do not type the key as a command argument):

   ```bash
   .venv/bin/python -B bin/enter_market_secret.py --approved-create --expected-account <approved-account>
   ```

   The helper checks account identity before prompting, refuses redirected input
   and echo fallback, calls `CreateSecret` once for exactly `fbs/the-odds-api-key`,
   and never updates an existing secret or prints the value. Creation failures or
   ambiguity stop; inspect metadata before any further approval/retry. It uses
   default Secrets Manager encryption, not a new customer-managed KMS key.
3. From metadata only, verify returned ARN account/region/name and generated suffix.
   Freeze its exact value and concrete parameter/policy hashes privately. The
   suffix is response-dependent; no fabricated ARN is deployed. Bind only
   `MarketSecretArn` in existing stack `fbs-stakeholder-insights`.
4. Use the **unchanged** template and existing reviewed ZIP/artifact. No upload or
   new CloudFormation resource is needed. Accept only the benchmark role's exact
   `GetSecretValue` addition, benchmark environment `MARKET_SECRET_ARN` change,
   and dependent ARN reevaluations. Reject replacements/additions/deletions,
   other direct changes or broader permissions. Preserve explanation resources,
   code, policies, configurations and all predecessor deployments.

Secret storage/requests and bounded AWS compute/storage/logging consume eligible
credits; account coverage must be checked before creation. No personal-payment
or zero-consumption assumption is made. Keep all schedules, rules, alarm actions,
notifications and public display disabled.

## Bounded capture, comparison and replay sequence

Minimum successful verification uses **two state-machine executions**, **five
weekly-worker calls** (four fresh stages plus one completed replay), **one
ingestion invocation/CFBD attempt**, and **four benchmark calls** (capture,
capture replay, comparison, comparison replay). One weekly saved-model scoring
batch; zero fits, Athena queries, LLM requests, outcome captures or calls to the
separate inference function. No automatic retries or replacement tokens.

Before starting and before capture, scoring and market work, check actual UTC.
If the latest start/cutoff has passed, do not consume remaining external work.
Do not change cutoff or tokens automatically: preserve evidence and prepare a
new proposal. A late observation is ineligible even if its underlying quote is
older. Replays may run after cutoff because they repeat no observation/scoring.

1. Execute the fixed weekly request once. Require verified
   `workflow_completed=true` with withheld approval, cloud capture lineage,
   unchanged history/train/holdout/aggregates and protected model. Verify new
   prediction-object `LastModified` strictly before cutoff. Empty eligibility
   stays empty and does not justify another request.
2. Capture current odds once, completing retrieval before cutoff. Verify exact
   raw/manifest hashes, quota, timestamps and normalization. Replay capture once;
   require identical bytes/metadata with no extra secret read or HTTP request.
3. Derive mappings from verified captured evidence using
   `src.features.market_mapping.build_event_map`. It matches exact home/away names
   and UTC kickoff, rejects duplicate events/games and reused event IDs, and never
   uses fuzzy names or invented IDs. Differences such as provider mascot suffixes
   require an explicitly reviewed team-ID-to-literal-provider-name crosswalk
   supported by both captured rows. Freeze the crosswalk, mappings, exclusions
   and input hashes; aliases cannot change orientation or kickoff. No new fetch.
4. Bind the actual weekly/market completion hashes, deterministic mapping and
   actual UTC `as_of` once. Select no outcomes. The required schema window starts
   November 20 at 00:00 UTC and ends at that actual `as_of`; it must not claim
   future observation. Freeze/hash the complete request before comparison.
5. Invoke benchmark and exact replay. Require original forecast cutoff, model
   observation, market retrieval/update strictly before cutoff, and kickoff after
   cutoff. Compare only shared eligible games. Zero overlaps is a valid measured
   gap, never grounds for recapture or relaxed names/timing. Replay must preserve
   bytes/metadata. Execute the single completed weekly replay last; no duplicate
   ingestion/scoring is allowed.

The report may show probability differences, shared coverage, exclusion reasons
and pending labels only. With no outcomes, no measured Brier/log-loss comparison
or market-outperformance claim is permitted. Later-outcome capture/evaluation is
deferred and separately authorized. Existing retrospective/unapproved flags persist.

## Call trace and preparation evidence

| Calls | Existing permission / proposed change |
| --- | --- |
| Private-bucket preflight | Existing bucket-restricted `GetBucketPublicAccessBlock` |
| Weekly/source/model/receipt GET and prediction HEAD | Existing explicit read domains, pinned trainer/model; HEAD uses `GetObject` |
| Optional completion/raw probes | Existing exact-prefix `ListBucket`, `MaxKeys=1`; oversized/unrelated probes denied |
| Claims, attempt checkpoint and benchmark outputs | Existing isolated stakeholder domains; conditional `IfNoneMatch=*`, no source/model writes |
| One secret GET on first capture | Sole new exact-ARN `GetSecretValue`; no secret writes, unrelated secret or KMS permissions |
| Mapping and response bindings | Local verified evidence only; no additional cloud/provider call |

Read-only CloudFormation validation passed. **160 exact IAM contexts** passed
against the candidate benchmark policy, including the previously traced helper
closure and intended-secret access/other-secret/write denials. Access Analyzer
reported zero errors and the existing literal conditional-write wildcard warning.
The IAM test used a clearly labeled example suffix, not a purported existing ARN;
the exact returned ARN must be revalidated before the future stack update.
No deployed policy changed. Existing Linux ZIP/template stay unchanged; new
mapping and hidden-entry helpers are local tooling, not new Lambda code.

On unexpected failure/ambiguity, stop new work and preserve evidence. Stop only
the new active weekly execution if needed; do not alter predecessor configuration.
Disable only benchmark on unexpected benchmark workload failure. Leave the verified
explanation function and predecessors unchanged. No retries, resource deletion,
permission expansion, new cutoff or paid access is authorized here.
