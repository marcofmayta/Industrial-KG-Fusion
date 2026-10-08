
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.evaluation import cluster_bootstrap


def validate_against_template(labels, template):

    if labels.pair_id.duplicated().any() or set(labels.pair_id) != set(template.pair_id):
        raise ValueError('Annotations must cover exactly the original review template.')
    immutable = [c for c in template.columns if c not in ['relevance','unsafe','reviewer','rationale']]
    if not set(immutable).issubset(labels.columns):
        raise ValueError('Annotation file is missing original pair metadata.')
    a = labels.set_index('pair_id').sort_index()
    b = template.set_index('pair_id').sort_index()
    for column in immutable:
        if column == 'pair_id':
            continue
        if not a[column].astype(str).equals(b[column].astype(str)):
            raise ValueError(f'Original review metadata was modified: {column}')
    return labels


def evaluate(labels, key):
    if key.duplicated(['method','query_id','rank']).any():
        raise ValueError('Ranking key has duplicate positions.')
    if 'query_id' in labels and labels.groupby('query_id').review_split.nunique().gt(1).any():
        raise ValueError('A query cannot belong to multiple review splits.')
    if labels.pair_id.duplicated().any() or set(labels.pair_id) != set(key.pair_id):
        raise ValueError('Supply exactly one annotation for every pooled pair.')
    grades = pd.to_numeric(labels.relevance, errors='coerce')
    if not grades.isin([0,1,2,3]).all():
        raise ValueError('All relevance grades must be integers 0–3; pending labels cannot be scored.')
    if not labels.unsafe.isin(['yes','no','uncertain']).all() or labels.reviewer.fillna('').str.strip().eq('').any():
        raise ValueError('Every pair needs a reviewer and a safety judgement.')
    labels = labels.copy()
    labels['relevance'] = grades
    joined = key.merge(labels[['pair_id','relevance','unsafe','reviewer','review_split']], on='pair_id', validate='many_to_one')
    ideal = joined[['query_id','pair_id','relevance']].drop_duplicates().groupby('query_id').relevance.apply(lambda x: sorted(x,reverse=True)[:10])
    rows = []
    for (method,query_id),g in joined.groupby(['method','query_id']):
        g = g.sort_values('rank')
        if list(g['rank']) != list(range(1,11)):
            raise ValueError('Expected complete top ten for each query/method.')
        discount = np.log2(np.arange(2,12))
        dcg = ((2**g.relevance.to_numpy()-1)/discount).sum()
        ideal_grades = np.asarray(ideal.loc[query_id])
        idcg = ((2**ideal_grades-1)/discount[:len(ideal_grades)]).sum()
        rows.append(dict(method=method, query_id=query_id, review_split=g.review_split.iloc[0],
            precision_at_10=float(g.relevance.ge(2).mean()), pooled_ndcg_at_10=float(dcg/idcg) if idcg else 0,
            unsafe_fraction=float(g.unsafe.eq('yes').mean()), uncertain_fraction=float(g.unsafe.eq('uncertain').mean())))
    return pd.DataFrame(rows)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--labels', type=Path, required=True, help='A separate completed copy of blinded_pairs.csv')
    p.add_argument('--split', choices=['development','confirmation'], required=True,
                   help='Evaluate one group; do not reveal confirmation during development.')
    args = p.parse_args()
    out = ROOT / 'results/independent_review'
    template = pd.read_csv(out / 'blinded_pairs.csv', keep_default_na=False)
    labels = validate_against_template(pd.read_csv(args.labels, keep_default_na=False), template)
    labels = labels.loc[labels.review_split.eq(args.split)]
    key = pd.read_csv(out / 'ranking_key_do_not_show_reviewers.csv')
    key = key.loc[key.pair_id.isin(labels.pair_id)]
    try:
        results = evaluate(labels, key)
    except ValueError as error:
        p.error(str(error))
    results.to_csv(out / f'human_{args.split}_per_query.csv', index=False)
    metrics = ['precision_at_10','pooled_ndcg_at_10','unsafe_fraction','uncertain_fraction']
    results.groupby('method')[metrics].mean().to_csv(out / f'human_{args.split}_metrics.csv')
    intervals = []
    for method,group in results.groupby('method'):
        for metric in metrics:
            samples = cluster_bootstrap(group[metric], group.query_id)
            low,high = np.quantile(samples,[.025,.975])
            intervals.append(dict(method=method,metric=metric,estimate=float(group[metric].mean()),
                ci95_low=float(low),ci95_high=float(high),resampling_unit='query',queries=len(group)))
    pd.DataFrame(intervals).to_csv(out / f'human_{args.split}_confidence_intervals.csv',index=False)
    print(results.groupby(['review_split','method']).mean(numeric_only=True).to_string())


if __name__ == '__main__':
    main()
