"""Execute notebooks in clean kernels and optionally compare two complete runs."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data import sha256, write_json
from tools.notebook_outputs import sanitize_outputs


def fingerprints():
    paths = sorted(p for directory in (ROOT / "data/processed", ROOT / "results")
                   for p in directory.rglob("*") if p.is_file())
    return {p.relative_to(ROOT).as_posix(): sha256(p) for p in paths}


def run():
    execution = []
    for path in sorted((ROOT / "notebooks").glob("0[0-8]_*.ipynb")):
        print(f"Executing {path.name}", flush=True)
        notebook = nbformat.read(path, as_version=4)
        source_hash = sha256(path)
        for cell in notebook.cells:
            if cell.cell_type == "code":
                cell.outputs = []
                cell.execution_count = None
        start = time.monotonic()
        client = NotebookClient(notebook, timeout=1800, kernel_name="python3",
                                resources={"metadata": {"path": str(ROOT / "notebooks")}})
        client.execute()
        if sha256(path) != source_hash:
            raise RuntimeError(f"Notebook changed during execution: {path.name}. Restart with fixed sources.")
        nbformat.write(sanitize_outputs(notebook, ROOT), path)
        elapsed = time.monotonic() - start
        execution.append({"notebook": path.name, "status": "passed", "seconds": round(elapsed, 2)})
        print(f"Passed {path.name} ({elapsed:.1f}s)", flush=True)
    from tools.automatic_relevance_review import main as automatic_screen
    from tools.build_review_app import main as build_review
    automatic_screen()
    build_review()
    if len(execution) != 9:
        raise RuntimeError("Expected nine canonical notebooks, including optimization and independent review.")
    return execution


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true", help="Execute twice and require identical scientific artifacts.")
    args = parser.parse_args()
    for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[variable] = "1"
    os.environ["PYTHONHASHSEED"] = "42"
    os.environ["IPYTHONDIR"] = str(ROOT / ".cache/ipython")
    os.environ["JUPYTER_RUNTIME_DIR"] = str(ROOT / ".cache/jupyter")
    (ROOT / ".cache/ipython").mkdir(parents=True, exist_ok=True)
    (ROOT / ".cache/jupyter").mkdir(parents=True, exist_ok=True)
    first = run()
    reference = fingerprints()
    write_json(ROOT / "docs/execution_log.json", {"runs": [first]})
    if args.verify:
        second = run()
        repeated = fingerprints()
        changed = [path for path in sorted(set(reference) | set(repeated)) if reference.get(path) != repeated.get(path)]
        verification = {"runs": 2, "clean_kernel_per_notebook": True,
                        "artifacts_checked": len(reference), "changed_artifacts": changed,
                        "identical": not changed, "sha256": repeated}
        write_json(ROOT / "docs/reproducibility.json", verification)
        write_json(ROOT / "docs/execution_log.json", {"runs": [first, second]})
        if changed:
            raise RuntimeError(f"Artifacts changed across runs: {changed}")
        print(f"Verified {len(reference)} identical artifacts across two clean runs.", flush=True)


if __name__ == "__main__":
    main()
