"""Build a blinded, unlabelled relevance pool and a stratified identity audit."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer, TfidfTransformer
from sklearn.feature_extraction import DictVectorizer
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data import write_json
from src.text_extraction import extract_asset_mentions
from src.retrieval import build_graph_features, mask_identifiers


def main():
    out = ROOT / 'results/independent_review'
    out.mkdir(parents=True, exist_ok=True)
    records = pd.read_csv(ROOT / 'results/text/record_audit.csv', keep_default_na=False)
    audit = []
    for row in records.itertuples():
        mentions = sorted(set(x[0] for x in extract_asset_mentions(row.combined_text)))
        status = ('missing_structured_id' if not row.equipment_id else
                  'no_textual_id' if not mentions else
                  'matching_only' if mentions == [row.equipment_id] else
                  'matching_with_other_mentions' if row.equipment_id in mentions else
                  'discordant_mentions')
        audit.append(dict(row_id=row.row_id, equipment_id=row.equipment_id,
                          textual_ids=' | '.join(mentions), identity_status=status))
    audit = pd.DataFrame(audit)
    audit.to_csv(out / 'identity_audit.csv', index=False)
    audit.groupby('identity_status').size().rename('records').to_csv(out / 'identity_summary.csv')
    sample = pd.concat([g.sample(n=min(20,len(g)), random_state=271828)
                        for _,g in audit.groupby('identity_status')])
    sample = sample.merge(records[['row_id','problem_text','action_text']], on='row_id')
    sample['reviewed_identity'] = ''
    sample['evidence'] = ''
    sample['reviewer'] = ''
    sample.to_csv(out / 'identity_review.csv', index=False)
    queries = pd.read_csv(ROOT / 'results/retrieval/optimization/confirmation_queries.csv', keep_default_na=False)
    all_candidates = pd.read_csv(ROOT / 'results/retrieval/asset/candidates.csv', keep_default_na=False)
    candidates = all_candidates.loc[~all_candidates.row_id.isin(queries.row_id)].reset_index(drop=True)
    # A solution-retrieval candidate must actually contain an intervention.
    action_by_id = records.set_index('row_id').action_text
    candidates = candidates.loc[action_by_id.loc[candidates.row_id].str.strip().ne('').to_numpy()].reset_index(drop=True)
    queries = queries.sample(n=40, random_state=271828).reset_index(drop=True)
    queries['review_split'] = ['development']*20 + ['confirmation']*20
    edges = pd.read_csv(ROOT / 'results/kg/edges.csv', keep_default_na=False, low_memory=False)
    by_id = records.set_index('row_id')
    # A real user presents the problem before its intervention is known.
    queries['masked_text'] = by_id.loc[queries.row_id, 'problem_text'].map(mask_identifiers).to_numpy()
    matrices = []
    for kwargs in [dict(ngram_range=(1,2), min_df=2, max_df=.98, max_features=30000),
                   dict(analyzer='char_wb', ngram_range=(3,5), min_df=3, max_features=60000)]:
        v = TfidfVectorizer(sublinear_tf=True, **kwargs)
        matrices.append((v.fit_transform(candidates.masked_text), v.transform(queries.masked_text)))
    v = DictVectorizer()
    t = TfidfTransformer()
    cg = build_graph_features(by_id.loc[candidates.row_id].reset_index(), edges)
    query_edges = edges.loc[edges.source_field.eq('WorkOrderDescription')]
    qg = build_graph_features(by_id.loc[queries.row_id].reset_index(), query_edges, include_structured=False)
    matrices.append((t.fit_transform(v.fit_transform(cg)), t.transform(v.transform(qg))))
    order = np.random.default_rng(42).permutation(len(candidates))
    ranking_rows, pairs = [], set()
    for method,(c,q) in zip(['word','character','graph_idf'], matrices):
        scores = (q @ c.T).toarray()
        for i,row in enumerate(queries.itertuples()):
            eligible = (candidates.row_id.ne(row.row_id) & candidates.work_order.ne(row.work_order)
                        & candidates.template.ne(row.template)).to_numpy()
            pool = order[eligible[order]]
            ranked = pool[np.argsort(-scores[i,pool], kind='stable')][:10]
            for rank,idx in enumerate(ranked,1):
                candidate_id = int(candidates.iloc[idx].row_id)
                pairs.add((int(row.row_id), candidate_id))
                ranking_rows.append(dict(method=method, query_id=int(row.row_id), candidate_id=candidate_id, rank=rank))
    hidden = pd.DataFrame(ranking_rows)
    review = []
    split = queries.set_index('row_id').review_split.to_dict()
    for query_id,candidate_id in sorted(pairs):
        query, candidate = by_id.loc[query_id], by_id.loc[candidate_id]
        review.append(dict(query_id=query_id,candidate_id=candidate_id,review_split=split[query_id],
                           query_problem=query.problem_text, candidate_problem=candidate.problem_text,
                           candidate_action=candidate.action_text, relevance='', unsafe='', reviewer='', rationale=''))
    review = pd.DataFrame(review).sample(frac=1, random_state=271828).reset_index(drop=True)
    review.insert(0,'pair_id', [f'PAIR_{i:04d}' for i in range(len(review))])
    review.to_csv(out / 'blinded_pairs.csv', index=False)
    hidden.merge(review[['query_id','candidate_id','pair_id']], on=['query_id','candidate_id']).to_csv(out / 'ranking_key_do_not_show_reviewers.csv', index=False)
    write_json(out / 'protocol.json', dict(seed=271828, queries=40, development_queries=20, confirmation_queries=20,
        candidates=len(candidates), candidate_requires_nonempty_action=True,
        pooled_pairs=len(review), methods=['word','character','graph_idf'], k=10,
        status='pending_independent_annotation', label_source='human review, never regex-derived',
        limitations='Same audited synthetic source; task measures technical relevance, not physical identity. Query does not expose its known intervention.',
        grades={'0':'irrelevant', '1':'related but intervention not directly reusable', '2':'useful with adaptation', '3':'directly useful'},
        unsafe_values=['yes','no','uncertain']))
    print('Prepared',len(review),'blinded pairs; identity strata:',audit.identity_status.value_counts().to_dict())


if __name__ == '__main__':
    main()
