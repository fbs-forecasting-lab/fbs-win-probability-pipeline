# PM-07 stakeholder adapters: local verification and external gaps

## Current status

Implementation starts from verified monitoring commit
`9510a56026294d6085611a4a831c9e355c0404aa` on
`feature/benchmarking-and-explanations`. The new explanation and moneyline
adapters are **not deployed or externally executed**. Existing PM-02 through
PM-06 verification remains historical predecessor evidence, not verification of
these new handlers. See the [contract](stakeholder-insights-contract.md) and
[runbook](cloud-stakeholder-runbook.md).

No model/provider invocation, odds/CFBD capture, outcome capture, Athena query,
fit, inference invocation, weekly execution, artifact upload or cloud mutation
ran for PM-07. Delivery controls and predecessors were not changed. No provider
secret value was retrieved; no subscription, access agreement, paid upgrade,
purchase or Organizations enrollment was activated.

## Newly executed local checks

| Check | Actual result |
| --- | --- |
| Full offline suite | **325 passed**, zero failures/errors; 44 new tests, 281 existing |
| Focused new tests | 15 explanation, 15 market, 10 capture/comparison and 4 package/policy tests passed |
| Local template validation and `cfn-lint` | Passed; exactly eight proposed resources |
| Package integrity | CRC passed; all 37 allowlisted project files match source bytes |
| Dependency closure | Twenty pinned versions reused unchanged from the verified predecessor |
| Native files | 250 ELF64 little-endian Linux x86_64 binaries; maximum required GLIBC symbol version 2.27 |
| Package size | 79,057,385 bytes compressed; 224,205,438 bytes uncompressed, below 262,144,000 bytes |
| New-handler Linux execution | **Not verified**; no usable local compatible Linux daemon; no AWS invocation authorized |

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

## Newly executed read-only AWS checks

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
| Explanation | Provider/model metadata, strict implementation, synthetic tests, package and scoped IAM | One approved real Converse call, actual usage/provenance, deployed Linux execution, replay and negative requests |
| Sportsbook capture | Current-endpoint adapter, provenance, synthetic normalization/timing tests, disabled-access refusal | Free provider account/key/quota verification, securely configured secret, separately reviewed exact-ARN IAM activation and one approved real current-market capture |
| Paired benchmark | Shared-cohort and timing gates, synthetic metric tests | Genuine eligible model/market observations before a common cutoff, explicit real event mappings and separately selected later outcomes |

Neither possible third-party credits nor a free advertised plan is treated as
proof of account access. Historical odds require paid access; no historical
purchase is proposed. The saved Week 13 cutoff, **2026-11-20T23:59:00Z**, has
passed. A newly retrieved current market is ineligible for that forecast even
if its quote update is older. Zero aligned games must remain zero. No real
provider-event IDs or aliases have been invented for the proposal.

The preserved monitoring report is a valid **input**, not a new PM-07 result:
65 raw games, 55 retained, ten quarantined, 53 technical scoring rows, and 53
pending labels with no rolling metrics. Its historical holdout reference is
unchanged. A local allowlisted fact catalog was built from that verified source;
it is explicitly not a provider-generated explanation. Future execution must
retain failed/insufficient states, withheld publication and all retrospective
flags.

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
remain unchanged. This candidate awaits deployment approval; the limited smoke
would verify the LLM application, not complete genuine sportsbook benchmarking
or approve operational forecasting.
