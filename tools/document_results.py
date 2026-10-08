
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    metrics = pd.read_csv(ROOT / 'results/retrieval/asset/metrics.csv').set_index('method')
    rows = ['| Representation | Hit@10 | MRR@50 |', '| --- | --- | --- |']
    for method in ('Graph context full', 'Masked TF-IDF', 'Hybrid RRF', 'Random expectation'):
        values = metrics.loc[method]
        rows.append(f"| {method} | {values['hit@10']:.3%} | {values['mrr@50']:.6f} |")
    sensor = json.loads((ROOT / 'results/sensor/summary.json').read_text(encoding='utf-8'))
    rows += ['', '| Sensor indicator | Value |', '| --- | --- |',
             f"| Documented failure periods overlapped | {sensor['failures_overlapped']}/{sensor['failure_windows']} |",
             f"| Eligible windows flagged | {sensor['candidate_fraction']:.3%} |"]
    path = ROOT / 'README.md'
    text = path.read_text(encoding='utf-8')
    start = '<!-- shared: results -->\n'
    prefix, tail = text.split(start, 1)
    _, suffix = tail.split('\n<!-- /shared -->', 1)
    path.write_text(prefix + start + '\n'.join(rows) + '\n<!-- /shared -->' + suffix, encoding='utf-8')
    from tools.build_readmes import main as build_readmes
    build_readmes()
    print('README results refreshed from saved artifacts.')


if __name__ == '__main__':
    main()
