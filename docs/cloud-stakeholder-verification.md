# PM-07 stakeholder adapters: verification and remaining market gaps

## Current status

Implementation starts from verified monitoring commit
`9510a56026294d6085611a4a831c9e355c0404aa` on
`feature/benchmarking-and-explanations`. **PM-07A deployed the eight-resource
candidate and verified a genuine Bedrock explanation plus replay/refusals.**
Market capture/comparison remains externally unverified and access-disabled.
Existing PM-02 through PM-06 results remain predecessor evidence. See the
[contract](stakeholder-insights-contract.md) and
[runbook](cloud-stakeholder-runbook.md).

## PM-07A cloud verification (November 20, 2026, Eastern time)

The approved proposal, baseline, template, ZIP, dependency pins and all 37 source
files matched commit `60315e54aeda52dca96ae5f0e0900802f403f6ad` before writes.
The ZIP was uploaded once with a conditional no-overwrite write and SHA-256
read-back verification. CloudFormation reached **CREATE_COMPLETE** with exactly
eight resources. Deployed code, environment, trust/inline policies, concurrency,
timeouts, retry configuration and private log retention matched the candidate.
The actual runtime ARN matched the protected weekly producer; `FunctionUpdate`
was checked separately without inventing a manual runtime ARN.

The preflight began at 04:34:24Z on November 21 UTC, which was November 20 locally.
The five smoke calls ran from 04:37:00Z through 04:38:09Z; final integrity checks
completed at 04:38:45Z. Private evidence is retained under
`data/processed/pm07a-deployment-20261121T043424Z/`. Raw provider records, private
resource identifiers, parameters, controller and detailed evidence remain ignored.

| Smoke step | Actual verified result |
| --- | --- |
| 1: genuine explanation | `completed`, explanation `available`; direct regional `amazon.nova-micro-v1:0` returned a valid selection of all seven allowlisted facts |
| 2: identical replay | Original completion and all eight claim/attempt/checkpoint/artifact objects preserved byte-for-byte with unchanged metadata; no second provider request |
| 3: invalid source hash | Expected `failed` at `verified_facts`, before provider work; only the separate request claim was written, with no attempt/completion |
| 4: conflicting original token | Expected `failed` at `request_validation`, before provider work; no object mutation |
| 5: unconfigured market | Expected `unavailable` at `access_refusal`, zero provider attempts, secret retrievals, HTTP requests or output writes |

Both handlers executed in AWS Linux, Python 3.14/x86_64. Totals were **four
explanation and one benchmark invocations**, **one** genuine Bedrock request and
no automatic retries. CloudWatch independently recorded those Lambda counts,
zero Lambda Errors, one `AWS/Bedrock` invocation and exactly the returned token
counts: **257 input, 42 output, 299 total**. Five Lambda REPORT lines corroborated
the invocation count. The request used 1,160 fact/instruction bytes against the
6,144-byte bound and 42 output tokens against the 128-token limit. Provider
latency was 300 ms. The actual provider request ID, response/usage, input/response
hashes, claim, consumed attempt and checkpoint are preserved and cross-verified.

| Function / step | REPORT duration | Billed duration | Maximum memory / configured |
| --- | ---: | ---: | ---: |
| Explanation: genuine call | 1,905.25 ms | 2,915 ms | 98 / 512 MiB |
| Explanation: replay | 466.71 ms | 467 ms | 99 / 512 MiB |
| Explanation: invalid source | 386.19 ms | 387 ms | 99 / 512 MiB |
| Explanation: conflict | 173.24 ms | 174 ms | 99 / 512 MiB |
| Market: unconfigured refusal | 2.26 ms | 5,727 ms | 276 / 1,536 MiB |

Initialization was 1,009.13 ms for explanation and 5,724.47 ms for the market
handler. The latter imports the benchmark dependency closure before its access
guard; it did not fetch data or execute a model. Duration and initialization are
reported separately rather than equating handler duration with billed compute.

The generated extractive summary retained all seven exact source statements:
historical model/baseline references; 53 pending and zero matched outcomes with
rolling performance not yet measurable; 65 raw, 55 retained, ten quarantined and
53 technical scoring rows; distribution samples 2,194 versus 53 with one
investigation indicator; and explicit unknown historical availability, withheld
publication, no drift conclusion, no retraining, approval or alert closure.
The model selected/ordered fact identifiers; no unrestricted provider prose or
new numerical claim was rendered. All four output artifacts and completion
hashes, checkpoint identity, usage and producer claim passed verification.

This run established a **successful genuine explanation**, rather than merely a
safe unavailable fallback. Invalid/truncated/provider-failure behavior remains
covered by offline tests; it was not forced through another provider request.
No authoritative metric, prediction, model or alert was changed. All four
retrospective/unapproved flags and false operational approval persisted.

All **87 protected source/model/monitoring objects** retained their bytes and
metadata, and all seven predecessor configurations and execution lists were
unchanged. Their Lambda metrics had no invocation datapoints in the test window.
There were zero odds/CFBD requests, outcome captures, Athena queries, fits,
model-inference invocations or weekly executions. Nine new private objects remain:
eight for the explanation and one invalid-source claim. No market object or
secret was created/read. The deployed benchmark role has no secret permission.

Both new functions remain active at reserved concurrency **one**. The weekly
schedule, monitoring event rule and alarm actions remain disabled; notifications
and public display remain off. Bucket ownership, encryption, versioning and all
four public-access blocks are unchanged. Credential-pattern and stakeholder
private-identifier checks passed. No subscription, agreement activation, upgrade,
purchase or Organizations enrollment occurred. The account remained **FREE /
ACTIVE**, reporting **$119.99** eligible credits before and after; this delayed
credit balance is not proof of zero service consumption or a settled bill.

Eight additional **private offline controller checks** passed, covering frozen
source/dependencies, account/access guards, empty-secret IAM, ordered budgets,
refusal acceptance and preservation of ambiguous invocation evidence. The
application/template/package were unchanged, so the prior 325-test suite was
not repeated for documentation-only updates. No workload failed unexpectedly and
no function needed shutdown. The four/one Lambda allowance and one-provider
allowance are exhausted; further workloads require separate authorization.

## Initial PM-07 local checks (historical implementation evidence)

| Check | Actual result |
| --- | --- |
| Full offline suite | **325 passed**, zero failures/errors; 44 new tests, 281 existing |
| Focused new tests | 15 explanation, 15 market, 10 capture/comparison and 4 package/policy tests passed |
| Local template validation and `cfn-lint` | Passed; exactly eight proposed resources |
| Package integrity | CRC passed; all 37 allowlisted project files match source bytes |
| Dependency closure | Twenty pinned versions reused unchanged from the verified predecessor |
| Native files | 250 ELF64 little-endian Linux x86_64 binaries; maximum required GLIBC symbol version 2.27 |
| Package size | 79,057,385 bytes compressed; 224,205,438 bytes uncompressed, below 262,144,000 bytes |
| New-handler Linux execution | Not verified at packaging; subsequently established by PM-07A above |

Commands used for the final offline pass and structural validation:

```bash
PYTHONPATH=/tmp/fbs-pm03-work/network-guard:. .venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B bin/package_cloud_stakeholder.py --validate-only
/private/tmp/fbs-pm02b-validation-tools/bin/cfn-lint infra/cloud-stakeholder.yaml
```

The extra `PYTHONPATH` entry installed an offline network guard in addition to
the tests' service fakes. It is private verification tooling, not a runtime or
repository dependency. The full suite took 13.542 seconds. Tests use fictional
market events and stubbed provider responses; none are genuine market prices or
externally generated explanations.

Regression coverage includes American/decimal conversion and proportional
overround removal; duplicate/mismatched events; missing markets and market
timestamps; equality/future cutoff boundaries; current odds against an old
cutoff; shared-cohort probability metrics; pending/insufficient labels; exact
fact selection and unsupported claims; unavailable distribution measurements;
provider failure, truncation and usage validation; immutable claims, replay,
interrupted publication and ambiguous-attempt refusal; and scoped policy
conditions. Existing model, source and monitoring behavior was not changed.

## Initial PM-07 read-only AWS checks (historical readiness evidence)

CloudFormation accepted the candidate template. Access Analyzer found no errors;
each role has one expected `WILDCARD_WITHOUT_LIKE_OPERATOR` warning for literal
`"*"` in the `s3:if-none-match` equality condition. This is the conditional-write
requirement, not an unrestricted resource grant.

All **217 exact IAM request-context simulations passed**. Checks traced the
selected weekly/source/model/monitoring closure; exact-key optional probes;
`HeadObject` under `GetObject`; all conditional claim/checkpoint/output writes;
and denials of oversized listings, unrelated prefixes/buckets, source/model
writes, cross-adapter writes, other models/regions, unconfigured secret access
and predecessor invocations. Proposed function and role names were unused.
These are template/policy simulations, not proof of effective deployed access.
Deployment must also recheck stack/log-name collisions and actual role behavior.

AWS account-plan metadata reported **FREE / ACTIVE** with eligible credits.
General billing investigation was not repeated. Amazon Nova Micro metadata
reported ACTIVE, direct on-demand support in `us-east-1`, authorized access and
available agreement/entitlement/region status. Quotas were positive: 200
on-demand requests/minute and 4,000,000 tokens/minute. No model was invoked and
no access agreement was accepted. These observations do not establish actual
runtime success, future service availability or zero credit consumption.

## External verification gaps

| Integration | Established now | Still required |
| --- | --- | --- |
| Explanation | PM-07A genuine Converse response/usage, AWS Linux execution, immutable replay, source/conflict refusals and exact fact rendering | No remaining gap for the bounded explanation smoke; free-form generation, ongoing operation and public delivery are not verified/approved |
| Sportsbook capture | Current-endpoint adapter, provenance, synthetic normalization/timing tests, disabled-access refusal | Free provider account/key/quota verification, securely configured secret, separately reviewed exact-ARN IAM activation and one approved real current-market capture |
| Paired benchmark | Shared-cohort and timing gates, synthetic metric tests | Genuine eligible model/market observations before a common cutoff, explicit real event mappings and separately selected later outcomes |

Neither possible third-party credits nor a free advertised plan is treated as
proof of account access. Historical odds require paid access; no historical
purchase is proposed. The saved Week 13 cutoff, **2026-11-20T23:59:00Z**, has
passed. A newly retrieved current market is ineligible for that forecast even
if its quote update is older. Zero aligned games must remain zero. No real
provider-event IDs or aliases have been invented for the proposal.

The preserved monitoring report is a valid **input**, not newly measured performance:
65 raw games, 55 retained, ten quarantined, 53 technical scoring rows, and 53
pending labels with no rolling metrics. Its historical holdout reference is
unchanged. A local allowlisted fact catalog was built from that verified source;
it is explicitly not a provider-generated explanation. PM-07A subsequently used
the genuine provider selection described above without changing those facts,
withheld publication or retrospective flags.

## Frozen deployment candidate

Private proposal and baselines are ignored under
`data/processed/pm07-readiness-20261120/`. The package is ignored at
`data/processed/pm07-package-20261120-final/cloud-stakeholder.zip`.
Earlier draft evidence remains preserved and is superseded by this candidate.

| File | SHA-256 |
| --- | --- |
| `deployment-proposal.json` | `6d3ca4baf7996d825fab8805dd0a5ae547a105e8447770ef834b08d7cde26c4c` |
| `approval-baselines.json` | `bf4897cd77547a5372ba4dbf5f5e1fe8b95b362e11ed222848d542660edf3993` |
| `infra/cloud-stakeholder.yaml` | `21600dc2e17360bc4e03ac885f630946d9e161002c588a2aacd68422411222c4` |
| Reviewed ZIP | `55b0ec8af283dab3a9ae67ca47f0ca528a7c87e2810bb89333530625463afdd7` |

Phase A proposes eight new resources, four explanation Lambda invocations and
one unconfigured-market refusal, with at most **one** real Bedrock request and
**zero** odds requests. The market-secret parameter stays empty and grants no
secret-read permission. Source/model data, predecessors and disabled delivery
remain unchanged. This exact candidate was approved and deployed in PM-07A;
its bounded explanation smoke passed. Genuine sportsbook benchmarking and
operational forecasting remain incomplete/unapproved.
