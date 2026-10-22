# Runnable examples

From the repository root, after installing `requirements.txt` in Python 3.14:

```bash
.venv/bin/python -B bin/synthetic_demo.py --run-dir data/processed/synthetic-demo --allow-retrospective-demo
```

`synthetic_demo.py` makes deterministic fictional snapshots, then calls the real
normalization, dataset, baseline, and prediction functions. It never requests
API data, loads `.env`, or uses AWS. See the root [README](../README.md) for the
output inventory and chronological splits. The six fixtures use the existing
CFBD wire schema solely for compatibility; their source/HTTP metadata is
simulated, and their provenance explicitly labels them synthetic.

Outputs must be in a new directory beneath `data/processed/`; existing paths and
symlink paths are refused. Results stay ignored by Git. Pick a different run
name to repeat the example. Synthetic metrics do not estimate real-world skill.
