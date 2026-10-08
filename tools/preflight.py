
import argparse
import json
from pathlib import Path
import sys
import importlib.metadata as metadata

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.data import sha256


def check_inputs(root=ROOT):
    root=Path(root)
    snapshot=json.loads((root/'data/raw/source_snapshot.json').read_text(encoding='utf-8'))
    rows=[]
    for filename,field in [('MetroPT3(AirCompressor).csv','metropt3_sha256'),('maintenance_sample.parquet','maintenance_sha256')]:
        path=root/'data/raw'/filename
        rows.append({'file':'data/raw/'+filename,'present':path.exists(),
            'expected_sha256':snapshot[field],'hash_matches':sha256(path)==snapshot[field] if path.exists() else False})
    return rows


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--environment',action='store_true')
    args=parser.parse_args()
    rows=check_inputs()
    print(json.dumps({'inputs':rows,'ready':all(r['hash_matches'] for r in rows)},indent=2))
    if args.environment:
        for line in (ROOT/'requirements.txt').read_text().splitlines():
            name,expected=line.split('==')
            try:
                actual=metadata.version(name)
            except metadata.PackageNotFoundError:
                actual='missing'
            print(name,'expected='+expected,'installed='+actual)
    if not all(r['hash_matches'] for r in rows):
        print('Restore the exact documented maintenance snapshot. A fresh source stream is not an equivalent sample.',file=sys.stderr)
        raise SystemExit(1)


if __name__=='__main__':
    main()
