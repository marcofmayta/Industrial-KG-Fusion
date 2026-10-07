"""Repeat extension in a fresh notebook kernel and compare its artifacts."""
from pathlib import Path
import sys
import nbformat
from nbclient import NotebookClient
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from src.data import sha256, write_json
from tools.notebook_outputs import sanitize_outputs
directory = root / 'results/retrieval/optimization'
before = {p.name: sha256(p) for p in sorted(directory.glob('*')) if p.is_file()}
path = root / 'notebooks/07_target_audit_and_optimization.ipynb'
n = nbformat.read(path, as_version=4)
NotebookClient(n, timeout=1800, kernel_name='python3', resources={'metadata': {'path': str(root / 'notebooks')}}).execute()
nbformat.write(sanitize_outputs(n, root), path)
after = {p.name: sha256(p) for p in sorted(directory.glob('*')) if p.is_file()}
write_json(root / 'docs/optimization_reproducibility.json', {'identical': before == after, 'artifacts_checked': len(after), 'sha256': after})
assert before == after, 'Optimization artifacts changed on repeat execution.'
print('Optimization artifacts identical:', len(after))
