# fbs-win-probability-pipeline
Serverless machine learning pipeline for weekly FBS win-probability forecasts with drift monitoring, sportsbook benchmarking, and strict pre-kickoff data controls.

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

## Development Notes

- Keep credentials and machine-specific settings in `.env`; never commit that file.
- Use only data available before kickoff when developing or evaluating forecasts. See `docs/data-leakage-policy.md` for the project policy as it is developed.
- Add or update tests in `tests/` when changing pipeline behavior.
