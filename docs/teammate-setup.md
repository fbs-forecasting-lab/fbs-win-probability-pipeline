# Teammate setup and private Initial Demo data handoff

These commands run from the repository root after you have GitHub access to
`fbs-forecasting-lab/fbs-win-probability-pipeline`. Install Python **3.14.x**,
clone the repository, and use your own virtual environment. The private data
handoff is a separate archive; cloning GitHub alone does not provide datasets,
models, or credentials. Ask Hampton for the archive and its companion checksum
through the project's private university storage. Redistribution permission for
CFBD data has not been independently verified; keep the handoff within the
authorized project group.

## Clone and install

macOS/Linux:

```bash
git clone https://github.com/fbs-forecasting-lab/fbs-win-probability-pipeline.git
cd fbs-win-probability-pipeline
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python --version
```

Windows PowerShell:

```powershell
git clone https://github.com/fbs-forecasting-lab/fbs-win-probability-pipeline.git
Set-Location fbs-win-probability-pipeline
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python --version
```

The version must start with `Python 3.14.`. Use your own `.venv`; do not copy
someone else's environment. PowerShell may require a process-scoped execution
policy adjustment before activating a local virtual environment; use your
institution's approved procedure. The Windows commands have not been executed
on this macOS workstation.

## Verify and extract the private handoff

For the September 24 handoff, place these two privately supplied files in the
directory **next to** your fresh clone:

- `fbs-initial-demo-data-handoff-921b09b.zip`
- `fbs-initial-demo-data-handoff-921b09b.sha256.txt`

The expected ZIP SHA-256 is
`fb98d0b1bb0ed302e9bdfc01f6921f779f590f23afadac8e70a3d2c9a75b8a0b`.
Its `HANDOFF-MANIFEST.json` records source commit
`921b09bb2772937732d532b63bc7a1e48499dd7f` and dataset ID
`8ecf7cf50b5f4ae68bde2ad902370b7528d327ed0919b5fed7a1211447c7e5c5`.
It contains exactly 36 data files under `data/` and two root metadata files.
No trained model or credential is included.

From the fresh clone, run the same command in macOS/Linux or PowerShell. It
verifies the companion checksum, exact membership, safe paths, file sizes, and
per-file hashes **before** extraction. It refuses symbolic links and conflicting
existing files. Matching files can be reused after an interrupted extraction.

```text
python -c '
from pathlib import Path, PurePosixPath
import hashlib, json, stat, sys, zipfile
archive, checksum = map(Path, sys.argv[1:])
expected = checksum.read_text().split()
assert len(expected) == 2 and expected[1] == archive.name
assert hashlib.sha256(archive.read_bytes()).hexdigest() == expected[0]
with zipfile.ZipFile(archive) as z:
    manifest = json.loads(z.read("HANDOFF-MANIFEST.json"))
    files = manifest["files"]
    names = {item["path"] for item in files}
    assert len(files) == len(names) == 36
    assert {i.filename for i in z.infolist()} == names | {"HANDOFF-MANIFEST.json", "HANDOFF-README.txt"}
    assert len(z.infolist()) == 38 and z.testzip() is None
    assert manifest["source_commit"] == "921b09bb2772937732d532b63bc7a1e48499dd7f"
    assert manifest["dataset_id"] == "8ecf7cf50b5f4ae68bde2ad902370b7528d327ed0919b5fed7a1211447c7e5c5"
    assert manifest["historical_availability_verified"] is False
    assert manifest["approved_for_point_in_time_forecasting"] is False
    for info in z.infolist():
        path = PurePosixPath(info.filename)
        assert not path.is_absolute() and ".." not in path.parts and not info.is_dir()
        assert "\\" not in info.filename and ":" not in info.filename
        assert not stat.S_ISLNK(info.external_attr >> 16)
    for item in files:
        path = PurePosixPath(item["path"])
        assert path.parts[0] == "data"
        content = z.read(item["path"])
        assert len(content) == item["bytes"]
        assert hashlib.sha256(content).hexdigest() == item["sha256"]
        target = Path(*path.parts)
        assert not any(parent.is_symlink() for parent in (target, *target.parents))
        assert not target.exists() or target.read_bytes() == content
    for item in files:
        target = Path(*PurePosixPath(item["path"]).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            with target.open("xb") as output:
                output.write(z.read(item["path"]))
        assert hashlib.sha256(target.read_bytes()).hexdigest() == item["sha256"]
print("Verified and extracted 36 data files; no existing file changed.")
' ../fbs-initial-demo-data-handoff-921b09b.zip ../fbs-initial-demo-data-handoff-921b09b.sha256.txt
```

The archive's `HANDOFF-README.txt` summarizes its contents; the manifest lists
all paths, sizes, hashes, selected snapshot IDs, and reference results. `data/raw/`,
`data/interim/`, and `data/processed/` are Git-ignored. Confirm this after
extraction with `git status --short` (it should still be empty).

## Offline validation and local model

With the virtual environment active, the entire suite needs no AWS or CFBD
credentials:

```text
python -m unittest discover -s tests -v
```

The handoff selects these exact six ingestion manifests:

| Input | Manifest path |
| --- | --- |
| 2021 full regular season | `data/raw/cfbd/games/season=2021/16cba29e664a496fb9ca9c7f6d23cb88.manifest.json` |
| 2022 full regular season | `data/raw/cfbd/games/season=2022/bbd6dd3559074ab1ad2b291859dd37c0.manifest.json` |
| 2023 full regular season | `data/raw/cfbd/games/season=2023/087a3002111c4a97abaad886ea5f760a.manifest.json` |
| 2024 full regular season | `data/raw/cfbd/games/season=2024/cb45f74c1ad14f8ea7f19323bb034866.manifest.json` |
| 2025 full regular season | `data/raw/cfbd/games/season=2025/1657e1334c044ff0957e8e246f712d82.manifest.json` |
| 2026 Week 4 saved sample | `data/raw/cfbd/games/season=2026/3b59d327dcb94e818b911b94902e0bd9.manifest.json` |

Validate the supplied snapshots, normalized bundles, and feature dataset with
the existing loaders; this command checks raw hashes, coverage, normalized
output contracts, dataset hashes/counts, and provenance:

```text
python -c 'from pathlib import Path; from src.features import games; from src.models.baseline import load_dataset; r=load_dataset("data/processed/demo-features-v1", allow_retrospective_demo=True)["report"]; paths=[Path("data/raw/cfbd/games")/("season="+str(y))/r["sources"][str(y)]["source"]["manifest_file"] for y in range(2021,2027)]; [games.normalize_snapshot(path) for path in paths]; print(r["dataset_id"], {k:v["output"] for k,v in r["splits"].items()})'
```

Expected dataset ID is the one above, with **2,194 train / 740 holdout / 57
saved-sample rows**. The saved 2026 sample is not a refreshed live forecast.

To rebuild deterministically without changing supplied files, use the six paths
from the table as arguments to the existing CLIs. These single-line commands
work in both shells:

```text
python -m src.features.games --manifest data/raw/cfbd/games/season=2021/16cba29e664a496fb9ca9c7f6d23cb88.manifest.json data/raw/cfbd/games/season=2022/bbd6dd3559074ab1ad2b291859dd37c0.manifest.json data/raw/cfbd/games/season=2023/087a3002111c4a97abaad886ea5f760a.manifest.json data/raw/cfbd/games/season=2024/cb45f74c1ad14f8ea7f19323bb034866.manifest.json data/raw/cfbd/games/season=2025/1657e1334c044ff0957e8e246f712d82.manifest.json data/raw/cfbd/games/season=2026/3b59d327dcb94e818b911b94902e0bd9.manifest.json --output-root data/interim/teammate-rebuild-v1
python -m src.features.dataset --manifest data/raw/cfbd/games/season=2021/16cba29e664a496fb9ca9c7f6d23cb88.manifest.json data/raw/cfbd/games/season=2022/bbd6dd3559074ab1ad2b291859dd37c0.manifest.json data/raw/cfbd/games/season=2023/087a3002111c4a97abaad886ea5f760a.manifest.json data/raw/cfbd/games/season=2024/cb45f74c1ad14f8ea7f19323bb034866.manifest.json data/raw/cfbd/games/season=2025/1657e1334c044ff0957e8e246f712d82.manifest.json data/raw/cfbd/games/season=2026/3b59d327dcb94e818b911b94902e0bd9.manifest.json --normalized-root data/interim/teammate-rebuild-v1 --output-dir data/processed/teammate-rebuild-v1 --allow-retrospective-demo
```

Compare every regenerated file with its supplied counterpart:

```text
python -c 'from pathlib import Path; import json, hashlib; r=json.loads(Path("data/processed/demo-features-v1/dataset_report.json").read_bytes()); sources=r["sources"]; pairs=[(Path("data/interim/cfbd/games")/item["source"]["snapshot_id"],Path("data/interim/teammate-rebuild-v1")/item["source"]["snapshot_id"]) for item in sources.values()]+[(Path("data/processed/demo-features-v1"),Path("data/processed/teammate-rebuild-v1"))]; assert_all=lambda a,b: all((b/p.name).read_bytes()==p.read_bytes() for p in a.iterdir()); assert all(assert_all(a,b) for a,b in pairs); print("Six normalized bundles and six dataset files match byte for byte.")'
```

Train and evaluate locally from the supplied feature dataset, then reload its
model for both prediction modes:

```text
python -m src.models.baseline --dataset-dir data/processed/demo-features-v1 --output-dir data/processed/teammate-baseline-v1 --allow-retrospective-demo
python -m src.models.predict --model-dir data/processed/teammate-baseline-v1 --prior-win-pct-diff 0.2 --prior-avg-margin-diff 7 --home-field 1 --allow-retrospective-demo
python -m src.models.predict --model-dir data/processed/teammate-baseline-v1 --dataset-dir data/processed/demo-features-v1 --output-dir data/processed/teammate-sample-predictions-v1 --allow-retrospective-demo
```

Open `data/processed/teammate-baseline-v1/evaluation.json` for holdout results;
`data/processed/teammate-baseline-v1/holdout_predictions.csv` and
`data/processed/teammate-sample-predictions-v1/predictions.csv` for saved
probabilities. The handoff manifest includes the previous reference metrics and
both sets of home/away probabilities. Compare each number with a tolerance of
`1e-12`; the hypothetical vector `(0.2, 7, 1)` should give home probability
about **0.662422294285731**. These inputs describe a hypothetical vector,
not an actual game. Training uses only the three documented predictors. The
source publication times remain unknown, so this retrospective demonstration
is not approved for point-in-time forecasting.

This command compares the locally trained model with the handoff's reference
values, including both probability columns for all 797 saved rows:

```text
python -c '
from pathlib import Path
import csv, json, sys, zipfile
from math import isclose
with zipfile.ZipFile(sys.argv[1]) as z:
    reference = json.loads(z.read("HANDOFF-MANIFEST.json"))["reference_results"]
model_dir = Path("data/processed/teammate-baseline-v1")
evaluation = json.loads((model_dir / "evaluation.json").read_bytes())
for group in ("model", "constant_baseline"):
    for metric in ("brier_score", "log_loss", "accuracy"):
        assert isclose(evaluation[group][metric], reference["evaluation"][group][metric], rel_tol=0, abs_tol=1e-12)
for filename in ("holdout_predictions.csv", "sample_predictions.csv"):
    with (model_dir / filename).open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected = reference["predictions"][filename]
    assert len(rows) == len(expected)
    for row, old in zip(rows, expected, strict=True):
        assert row["game_id"] == old["game_id"]
        for field in ("home_win_probability", "away_win_probability"):
            assert isclose(float(row[field]), old[field], rel_tol=0, abs_tol=1e-12)
print("Reference metrics and both probabilities for 740 holdout and 57 sample rows match.")
' ../fbs-initial-demo-data-handoff-921b09b.zip
```

A fresh CFBD ingestion request requires your own `CFBD_API_KEY`; it is not
needed for the steps above. S3 operations require separately authorized access
to a project bucket and a local region/prefix setting; repository access does
not grant access to another student's AWS bucket. This handoff does not
configure cloud access.

## Daily Git collaboration

When your working tree is clean, update main with `git switch main` and
`git pull --ff-only origin main`. Start a task branch with
`git switch -c feature/my-task` (replace `my-task` with your task name), make
focused changes, and review
`git status --short` and `git diff --check`. Stage and commit only intended
code/docs, then `git push -u origin feature/my-task` and open a PR into main.
Do not put `.env`, `.venv`, raw/interim/processed data, or model artifacts in
Git. If you have local changes, preserve them while planning the update; do
not use clean/reset commands as routine setup.

On filesystems without same-volume hard-link support, the existing atomic
no-overwrite publisher used by normalization, datasets, and models may fail.
The macOS fresh-clone test below verifies this workstation's filesystem only;
Windows and other filesystem configurations need their own test. If you see
an error about hard links or output publication, report the exact filesystem
and error before changing the pipeline or Python/dependency versions.
