
import argparse
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data import sha256, write_json
from src.graph_quality import graph_quality_report
from src.temporal_lineage import temporal_lineage
from src.evaluation import bootstrap_ci, paired_comparisons, lift_intervals


def compare_frames(actual, expected, keys):
    a, b = actual.set_index(keys).sort_index(), expected.set_index(keys).sort_index()
    if not a.index.equals(b.index) or set(a.columns) != set(b.columns):
        return False
    for column in a:
        if pd.api.types.is_numeric_dtype(a[column]) and pd.api.types.is_numeric_dtype(b[column]):
            if not np.allclose(a[column], b[column], atol=1e-12, rtol=1e-12, equal_nan=True):
                return False
        elif not a[column].astype(str).equals(b[column].astype(str)):
            return False
    return True


def verify_results():
    checks = []
    def check(name, passed, artifact, computation):
        checks.append(dict(result=name, passed=bool(passed), artifact=artifact, computation=computation))
    for folder, group in [('retrieval/asset', ['method']), ('retrieval/diagnostic', ['split', 'method']),
                          ('retrieval/optimization/development', ['method']), ('retrieval/optimization/confirmation', ['method'])]:
        if folder.endswith(('development', 'confirmation')):
            path = ROOT / 'results' / (folder+'_per_query.csv')
            target = ROOT/'results'/(folder+'_metrics.csv')
        else:
            path = ROOT/'results'/folder/'per_query.csv'; target = ROOT/'results'/folder/'metrics.csv'
        frame = pd.read_csv(path)
        expected = pd.read_csv(target)
        columns = [c for c in expected if c not in group]
        actual = frame.groupby(group)[columns].mean().reset_index()
        check('All means: '+folder, compare_frames(actual, expected, group), target.relative_to(ROOT).as_posix(), 'group means of saved per-query metrics')
    asset = ROOT/'results/retrieval/asset'
    per = pd.read_csv(asset/'per_query.csv')
    metrics = [c for c in per if c.startswith(('hit@', 'mrr@'))]
    ci = bootstrap_ci(per, metrics)
    check('Asset bootstrap intervals', compare_frames(ci, pd.read_csv(asset/'confidence_intervals.csv'), ['method', 'metric']), 'results/retrieval/asset/confidence_intervals.csv', 'src.evaluation.bootstrap_ci; 500 asset-cluster resamples, seed 42')
    differences = pd.read_csv(asset/'paired_differences.csv')
    pairs = list(differences[['left', 'right']].drop_duplicates().itertuples(index=False, name=None))
    check('Asset paired differences', compare_frames(paired_comparisons(per, metrics, pairs), differences, ['left', 'right', 'metric']), 'results/retrieval/asset/paired_differences.csv', 'src.evaluation.paired_comparisons')
    check('Asset lift intervals', compare_frames(lift_intervals(per, metrics), pd.read_csv(asset/'lift.csv'), ['method', 'metric']), 'results/retrieval/asset/lift.csv', 'src.evaluation.lift_intervals')
    test = pd.read_csv(ROOT/'results/retrieval/optimization/confirmation_per_query.csv')
    diff = pd.read_csv(ROOT/'results/retrieval/optimization/paired_differences.csv')
    pairs = list(diff[['left', 'right']].drop_duplicates().itertuples(index=False, name=None))
    check('Optimization paired differences', compare_frames(paired_comparisons(test, ['hit@10', 'mrr@50'], pairs), diff, ['left', 'right', 'metric']), 'results/retrieval/optimization/paired_differences.csv', 'src.evaluation.paired_comparisons')
    records = pd.read_csv(ROOT/'results/text/record_audit.csv', keep_default_na=False)
    entities = pd.read_csv(ROOT/'results/text/entities.csv', keep_default_na=False)
    summary = json.loads((ROOT/'results/text/summary.json').read_text())
    check('Text counts', len(records) == summary['records'] and len(entities) == summary['entities'] and len(pd.read_csv(ROOT/'results/text/exact_duplicates.csv')) == summary['exact_duplicates_removed'], 'results/text/summary.json', 'count record, entity and duplicate artifacts')
    coverage = pd.read_csv(ROOT/'results/text/extraction_coverage.csv')
    actual = pd.DataFrame([dict(entity_type=r.entity_type, records_with_entity=int(records['n_'+r.entity_type].gt(0).sum()), coverage=float(records['n_'+r.entity_type].gt(0).mean())) for r in coverage.itertuples()])
    check('Entity coverage', compare_frames(actual, coverage, ['entity_type']), 'results/text/extraction_coverage.csv', 'presence in record_audit; not extraction accuracy')
    identity = pd.read_csv(ROOT/'results/independent_review/identity_audit.csv', keep_default_na=False)
    counts = identity.groupby('identity_status').size().rename('records').reset_index()
    check('Identity strata', compare_frames(counts, pd.read_csv(ROOT/'results/independent_review/identity_summary.csv'), ['identity_status']), 'results/independent_review/identity_summary.csv', 'group identity_audit records')
    events = pd.read_csv(ROOT/'results/sensor/events.csv')
    sensor = json.loads((ROOT/'results/sensor/summary.json').read_text())
    overlap = pd.read_csv(ROOT/'results/sensor/failure_overlap.csv')
    check('Sensor event and overlap counts', len(events) == sensor['events'] and int(overlap.detected_during_failure.sum()) == sensor['failures_overlapped'], 'results/sensor/summary.json', 'event rows and saved overlap indicators')
    check('Sensor alert fraction', np.isclose(sensor['candidate_windows']/sensor['eligible_windows'], sensor['candidate_fraction']), 'results/sensor/summary.json', 'candidate / eligible windows')
    check('Sensor durations', np.isclose(events.duration_min.sum()/60, sensor['event_span_hours']) and np.isclose(sensor['candidate_windows']*5/60, sensor['eventized_observed_hours']), 'results/sensor/summary.json', 'sum durations and five-minute observed candidate windows')
    cohort = pd.read_csv(asset/'cohort.csv'); candidates = pd.read_csv(asset/'candidates.csv'); queries = pd.read_csv(asset/'queries.csv')
    asset_summary = json.loads((asset/'summary.json').read_text())
    valid_counts = all(len(frame) == asset_summary[key] for frame, key in [(cohort, 'cohort_records'), (candidates, 'candidate_records'), (queries, 'query_records')])
    valid_counts &= all(frame.equipment_id.nunique() == asset_summary[key] for frame, key in [(cohort, 'cohort_assets'), (candidates, 'candidate_assets'), (queries, 'query_assets')])
    check('Asset cohort and query counts', valid_counts, 'results/retrieval/asset/summary.json', 'count saved cohort/index/query rows and distinct labels')
    check('Query index separation', not set(queries.row_id) & set(candidates.row_id) and not set(queries.work_order) & set(candidates.work_order), 'results/retrieval/asset/queries.csv', 'saved row/work-order intersection')
    check('Alert overlap and review count', len(overlap) == sensor['failure_windows'] and len(pd.read_csv(ROOT/'results/independent_review/blinded_pairs.csv')) == json.loads((ROOT/'results/independent_review/protocol.json').read_text())['pooled_pairs'], 'results/independent_review/protocol.json', 'count overlap periods and unique review pairs')
    for dataset in ['metropt3', 'maintenance']:
        processed = ROOT/'data/processed'/(dataset+'.parquet')
        if processed.exists():
            manifest = json.loads((ROOT/'results/data_manifest.json').read_text())
            check('Processed source rows: '+dataset, pq.read_metadata(processed).num_rows == manifest[dataset]['rows'], 'results/data_manifest.json', 'Parquet metadata against source manifest')
    for raw, field in [('maintenance_sample.parquet', 'maintenance_sha256'), ('MetroPT3(AirCompressor).csv', 'metropt3_sha256')]:
        path = ROOT/'data/raw'/raw
        if path.exists():
            snapshot = json.loads((ROOT/'data/raw/source_snapshot.json').read_text())
            check('Raw snapshot: '+raw, sha256(path) == snapshot[field], 'data/raw/'+raw, 'streaming SHA-256 against source_snapshot.json')
    report = {'scope': 'Saved-artifact recomputation; does not re-run retrieval ranks or validate human labels',
            'checks': checks, 'passed': all(c['passed'] for c in checks), 'checks_count': len(checks)}
    write_json(ROOT/'results/result_verification.json', report)
    print('Saved-result checks:', len(checks), 'passed:', report['passed'], flush=True)
    if not report['passed']:
        raise ValueError('Saved results failed verification; previous values were not modified.')


def build_supplements():
    nodes = pd.read_csv(ROOT/'results/kg/nodes.csv', keep_default_na=False)
    edges = pd.read_csv(ROOT/'results/kg/edges.csv', keep_default_na=False, low_memory=False)
    report, provenance = graph_quality_report(nodes, edges)
    report['input_sha256'] = {p: sha256(ROOT/p) for p in ['results/kg/nodes.csv', 'results/kg/edges.csv', 'config/kg_schema.json']}
    write_json(ROOT/'results/graph_quality_report.json', report)
    pd.DataFrame([dict(check=k, violations=v, passed=v == 0) for k, v in report['checks'].items()]).to_csv(ROOT/'results/graph_quality_report.csv', index=False)
    provenance.to_csv(ROOT/'results/kg/provenance_summary.csv', index=False)
    if not report['passed']:
        raise ValueError('Graph schema validation failed; inspect the additive report.')
    events = pd.read_csv(ROOT/'results/sensor/events.csv')
    windows = pd.read_parquet(ROOT/'results/sensor/window_scores.parquet')
    sensor_path = ROOT/'data/processed/metropt3.parquet'
    observations = pd.read_parquet(sensor_path, columns=['timestamp']).timestamp if sensor_path.exists() else None
    membership, adjacency = temporal_lineage(events, windows, observations)
    output = ROOT/'results/temporal'; output.mkdir(parents=True, exist_ok=True)
    membership.to_csv(output/'event_window_membership.csv', index=False)
    adjacency.to_csv(output/'event_order.csv', index=False)
    write_json(output/'provenance.json', dict(version='temporal-lineage-1', events=len(events), candidate_windows=len(membership), adjacency_edges=len(adjacency),
        interval_semantics='[start,end), source-local timezone unspecified; merged gaps are not inserted as observed windows',
        source_sha256={p: sha256(ROOT/p) for p in ['results/sensor/events.csv', 'results/sensor/window_scores.parquet']},
        observation_reference='zero-based row offsets in stable timestamp-sorted data/processed/metropt3.parquet' if observations is not None else 'unavailable',
        observation_sha256=sha256(sensor_path) if sensor_path.exists() else None,
        raw_snapshot_manifest='data/raw/source_snapshot.json',
        scope='Chronological adjacency and observation lineage; no temporal prediction, cross-source joining or causal reasoning'))
    print('Graph quality passed. Temporal windows:', len(membership), 'adjacencies:', len(adjacency), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build-supplements', action='store_true', help='Requires regenerated graph edges and sensor windows; original outputs are not modified.')
    args = parser.parse_args()
    verify_results()
    if args.build_supplements:
        build_supplements()


if __name__ == '__main__':
    main()
