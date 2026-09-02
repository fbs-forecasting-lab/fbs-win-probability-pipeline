# Data

This directory documents data used by the FBS win-probability pipeline.

Raw and generated datasets should not be committed to GitHub. Local data should be organized under directories such as:

- `raw/` — unmodified API responses or source extracts
- `interim/` — intermediate transformation outputs
- `processed/` — model-ready datasets

These directories are excluded from version control.

Production data will ultimately be stored and accessed through the project's cloud data pipeline.
