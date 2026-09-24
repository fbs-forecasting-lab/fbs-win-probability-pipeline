# fbs-win-probability-pipeline
Semester project building toward a serverless machine learning pipeline for weekly FBS win-probability forecasts with drift monitoring, sportsbook benchmarking, and strict pre-kickoff data controls.

Current implementation: CFBD games ingestion, local raw snapshot storage, validated per-snapshot game normalization, and explicitly permitted retrospective demo feature datasets, with offline tests. Model training, win-probability prediction, evaluation, monitoring, and serverless orchestration remain planned. Historical predictor availability is unverified.

## Environment Setup

Use Python 3.14.x for local development so your environment matches the pinned dependencies in `requirements.txt`.

### 1. Create a virtual environment

macOS/Linux:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install project dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Create your local environment file

Copy the example environment file and then fill in the required values for your machine and accounts.

macOS/Linux:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

### 4. Verify the environment

Run this command after setup to confirm that Python 3.14 is active and the required packages import successfully:

```bash
python -c "import sys, numpy, pandas, scipy, sklearn, matplotlib, requests, dotenv, boto3; print(sys.version)"
```

## Repository Structure

```text
src/        Pipeline code: ingestion, features, models, evaluation, and monitoring.
tests/      Automated tests for the pipeline.
notebooks/  Exploratory analysis and experiments.
data/       Local data guidance and data-related artifacts.
docs/       Architecture, model, stakeholder, and data-leakage documentation.
```

## Initial Demo: CFBD Ingestion and Storage

From the repository root, activate the existing environment and configure
`CFBD_API_KEY` in your environment or the project-root `.env` file. An existing
environment variable takes precedence, including an explicitly empty value.
The key is never a CLI argument. Do not share it or enable HTTP header debugging.

```bash
source .venv/bin/activate
python -m src.ingestion.cfbd --season 2025
```

The client calls `GET https://api.collegefootballdata.com/games` with Bearer
authentication and `year=2025`, `seasonType=regular`, `classification=fbs`.
It adds `week` only when `--week` is supplied. The contract was checked against
[CFBD's official Games documentation](https://apinext.collegefootballdata.com/api/games)
on September 23, 2026.

For a 2026 sample, first obtain the week from the authenticated CFBD calendar
(`GET https://api.collegefootballdata.com/calendar?year=2026`). Select a
`seasonType=regular` entry whose `startDate`/`endDate` contain the current date;
if none does, use the most recent completed regular-season calendar entry.
Record the selected `week` and calendar dates. If the calendar cannot be accessed
or supplies no valid current/recent entry, stop this verification and report the
blocker; do not guess a week or substitute another source. This lookup is a
verification step, not part of the ingestion CLI.

After setting `CFBD_WEEK` to that calendar-confirmed week, this command also
demonstrates the optional output directory:

```bash
python -m src.ingestion.cfbd --season 2026 --week "$CFBD_WEEK" --output-dir data/raw/cfbd/games
```

Each invocation publishes a new pair, with no overwrite:

```text
data/raw/cfbd/games/season=YYYY/<snapshot_id>.json
data/raw/cfbd/games/season=YYYY/<snapshot_id>.manifest.json
```

`--output-dir` replaces the games root; `season=YYYY` is appended. Relative custom
paths are relative to the working directory. Keep custom outputs under ignored
`data/raw/` or outside the repository. The default is anchored to the repository.
The CLI prints paths, counts, and field/classification coverage. Empty responses
are saved and explicitly marked **empty**, not treated as a passed coverage check.
Exit code 0 means the snapshot was stored; it does not certify data quality or
predictor suitability. Request, validation, and storage errors return exit code 1.

Offline tests require no key or network:

```bash
.venv/bin/python -B -m unittest discover -s tests -v
```

Tests reload saved JSON and validate counts and SHA-256, raw-field preservation,
no-overwrite/atomic publication, coverage, empty results, credential precedence,
sanitized failures, and bounded retries. See [data/README.md](data/README.md) for
the schema, provenance limitations, storage behavior, and reload verification.

Verification on September 23, 2026: offline tests passed on Python 3.14.2.
Authenticated live requests saved 888 games for 2025 and 71 games for 2026
regular-season Week 4, selected from CFBD's official 2026 calendar. Both snapshots
passed reload, SHA-256, count, and coverage checks. All 16 tracked fields were
present and no duplicate IDs were found. CFBD reported the Academic tier with a
3,000-call monthly quota and 2,997 calls remaining after verification, shared
across football and basketball. These are point-in-time observations, not a
guarantee of future quota or source completeness. See [data/README.md](data/README.md)
for exact commands, snapshot IDs, classification counts, and the quota reset time.

## Initial Demo: Game Normalization

Normalization runs entirely offline against explicitly selected ingestion
manifests. It verifies the raw hash, count, recomputed coverage, and metadata;
validates the 16 tracked game fields; and keeps regular-season FBS-versus-FBS
games. Invalid rows are quarantined separately from valid non-FBS exclusions.

From the repository root, process the two saved snapshots separately:

```bash
.venv/bin/python -B -m src.features.games --manifest \
  data/raw/cfbd/games/season=2025/1657e1334c044ff0957e8e246f712d82.manifest.json \
  data/raw/cfbd/games/season=2026/3b59d327dcb94e818b911b94902e0bd9.manifest.json
```

The CLI accepts one or more paths after `--manifest`, or repeated `--manifest`
options. `--output-root data/interim/cfbd/games-review` selects an alternate root;
each snapshot still receives its own subdirectory. No snapshot is automatically
selected or merged. No API key or network is needed.

Each `data/interim/cfbd/games/<snapshot_id>/` directory contains `games.csv`,
`exclusions.json` (separate excluded/quarantined lists), and `quality_report.json`.
Identical reruns preserve output bytes and existing files; conflicting output
is rejected without overwriting it. Empty outputs still include CSV headers.
CLI exit code 1 means at least one input failed; other explicit inputs are still
processed. Exit code 0 can include quarantined rows or an empty table, so inspect
the quality report rather than treating the exit code as data-quality approval.

Offline verification retained 762 of 888 games for 2025 and 58 of 71 games for
2026 Week 4. The remaining 126 and 13 games were valid FBS–FCS exclusions, with
zero quarantines. These match the earlier raw FBS–FBS counts. Normalization
preserves unknown historical availability and does not approve predictor use.

Run the complete offline suite:

```bash
.venv/bin/python -B -m unittest discover -s tests -v
```

See [the data dictionary](docs/data-dictionary.md) for column types and validation,
[the leakage policy](docs/data-leakage-policy.md) for time and outcome boundaries,
and [data/README.md](data/README.md) for output verification and exact paths.

## Initial Demo: Retrospective Feature Datasets

`src.features.dataset` connects the six selected 2021–2026 snapshots to three
predictors, using each team's completed regular-season FBS–FBS games from exactly
the previous season. Joins use team IDs. The explicit predictor order is
`prior_win_pct_diff`, `prior_avg_margin_diff`, `home_field`; scores, labels,
sample counts, and provenance are audit fields, not additional predictors.

The builder requires one explicit manifest per season, existing verified
normalization outputs, an output directory, and `--allow-retrospective-demo`.
Use the [exact six-snapshot command](data/README.md#retrospective-demo-datasets-schema-version-1)
from the repository root. It runs offline and writes six artifacts under ignored
`data/processed/demo-features-v1/`. Identical reruns preserve existing files;
conflicting output is rejected.

The saved snapshots produced 2,194 labeled training rows (2022–2024), 740 labeled
holdout rows (2025), and 57 unlabeled prediction-input rows (2026 Week 4), plus
664 team-season aggregate audit rows. Dataset eligibility excluded 43, 22, and
1 target rows respectively. These counts follow normalization exclusions and
quarantines; see the dataset report for both stages.

All outputs are marked `retrospective_demo`, historical availability unverified,
and not approved for point-in-time forecasting. The cutoff is the selected
snapshot's scheduled kickoff. Earlier scheduled starts prove chronology only;
historical schedule versions, result publication/completion times, and revisions
remain unverified. The flag permits this documented reconstruction assumption;
it does not grant predictor approval or establish leakage-safe backtesting.

Verification on September 23, 2026: 70 offline tests passed on Python 3.14.2.
Tests include prior-season aggregation, missing histories, outcome isolation,
split boundaries, chronology, provenance, and repeatable publication. No model
has been trained and no performance claim is made.

## Development Notes

- Keep credentials and machine-specific settings in `.env`; never commit that file.
- Use only data demonstrably available before the defined forecast cutoff when developing or evaluating forecasts. See `docs/data-leakage-policy.md` for current boundaries and remaining work.
- Add or update tests in `tests/` when changing pipeline behavior.
