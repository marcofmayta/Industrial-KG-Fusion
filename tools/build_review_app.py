"""Build an offline annotation page without exposing methods or ranks."""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    pairs = pd.read_csv(ROOT / 'results/independent_review/blinded_pairs.csv', keep_default_na=False)
    template = (ROOT / 'tools/review_app.html').read_text(encoding='utf-8')
    payload = json.dumps(pairs.to_dict('records'), ensure_ascii=False).replace('<', '\\u003c')
    output = ROOT / 'review/index.html'
    output.parent.mkdir(exist_ok=True)
    output.write_text(template.replace('__PAIRS__', payload), encoding='utf-8')
    print('Offline review:', output)


if __name__ == '__main__':
    main()
