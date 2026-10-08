# Reproducibility and data access

## Local full execution

Python 3.12; installed direct dependencies matched every pin in `requirements.txt` in the local execution environment. A new isolated environment installation and remote CI execution were not performed. CI configuration runs methodological tests on Windows and Linux; it does not certify full pipeline reproduction.

```powershell
python -m pip install -r requirements.txt
python tools/preflight.py --environment
python -m unittest discover -s tests
python tools/run_pipeline.py
python tools/run_pipeline.py --verify
```

The runner checks **both exact raw hashes before starting any notebook**. MetroPT is publicly downloadable from the UCI URL in `src/config.py` using `src.data.download_metropt`; the loader itself can download it, but runner preflight requires acquisition before a full run. For example:

```powershell
python -c "from src.data import download_metropt; download_metropt('data/raw')"
```

The 50000-row maintenance Parquet snapshot is not distributed in Git. Restore `data/raw/maintenance_sample.parquet` from the project's retained snapshot and compare its SHA-256 with `data/raw/source_snapshot.json`. The source is public synthetic maintenance, but its upstream revision is unknown. There is **no verified command to recreate the exact historical sample from a fresh upstream stream**. A new sample requires its own manifest and experiment version; it is not equivalent reproduction.

The local copies passed preflight. That fact does not make the repository self-contained for another researcher. Exact snapshot availability and redistribution terms must be resolved before claiming public end-to-end reproducibility. MetroPT attribution is documented in the manifest; no repository software license was supplied, and licensing remains an author decision.

## Saved-artifact verification

```powershell
python tools/research_audit.py
# Requires regenerated graph edges and sensor-window Parquet:
python tools/research_audit.py --build-supplements
```

The first command recalculates means, cluster intervals, paired differences, lifts and counts from saved artifacts. It cannot reconstruct original rankings or prove annotation validity. The second validates actual graph files and exports temporal lineage. Large graph edges and processed data remain excluded from Git and can only be regenerated once the raw snapshot is available.

## Versions and result preservation

`docs/audit_baseline.json` records the 77 pre-audit scientific-file hashes. Retained experiments preserve their original numerical outputs. Five historical screening artifacts were retired; their hashes remain in the baseline as historical records, with the removal documented in `docs/RESULT_CHANGELOG.md`. New graph-quality and temporal artifacts are additive; PRECEDES is not inserted into the original graph. The runner preserves previous results in `archive/runs/<run-id>/results.zip` before re-execution, with old/new hashes, exact old value files and responsible source hashes. `docs/RESULT_CHANGELOG.md` records changes, including partial runs. Local archives are ignored by Git; exporting a changed experiment requires distributing its provenance deliberately.

Historical two-run verification of 54 artifacts applies to 00–06. Separate repetition records apply to 07 and 08. Saved-artifact verification recomputes statistics and supplements separately from rankings. A subsequent complete execution passed all nine notebooks in separate clean kernels; all 85 scientific input/output hashes remained unchanged. This single execution does not replace the historical two-run records.

Seeds: 42 for canonical sampling/ties/bootstrap; 314159 for optimization confirmation selection; 271828 for review selection/order. Shared index exposure, synthetic templates, fixed-seed conditioning and lack of external ground truth remain scientific limitations.
