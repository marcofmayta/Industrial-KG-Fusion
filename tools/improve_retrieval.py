
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer, TfidfTransformer
from sklearn.feature_extraction import DictVectorizer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data import write_json, sha256
from src.retrieval import build_graph_features
from src.evaluation import evaluate_rankings, paired_comparisons, random_expectation


def main():
    out = ROOT / 'results/retrieval/optimization'
    out.mkdir(parents=True, exist_ok=True)
    previous = ROOT / 'results/retrieval/asset'
    candidates = pd.read_csv(previous / 'candidates.csv', keep_default_na=False)
    development = pd.read_csv(previous / 'queries.csv', keep_default_na=False)
    confirmation = candidates.sample(n=1500, random_state=314159).sort_values('row_id')
    candidates = candidates.loc[~candidates.row_id.isin(confirmation.row_id)].reset_index(drop=True)
    development = development.reset_index(drop=True)
    confirmation = confirmation.reset_index(drop=True)
    assert not set(confirmation.row_id) & set(development.row_id)
    assert not set(confirmation.row_id) & set(candidates.row_id)
    confirmation.to_csv(out / 'confirmation_queries.csv', index=False)
    write_json(out / 'protocol.json', {
        'seed': 314159, 'selection_metric': 'mrr@50',
        'development_queries': len(development), 'confirmation_queries': len(confirmation),
        'candidate_count': len(candidates), 'exclude_same_template': True,
        'limitations': 'New query rows from an already audited synthetic dataset; not an external blind test.',
        'baseline_source_sha256': sha256(previous / 'queries.csv'),
        'methods': ['word', 'character', 'graph_idf', 'word_character', 'word_graph', 'word_character_graph']})
    queries = pd.concat([development, confirmation], ignore_index=True)
    word = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=.98,
                           max_features=30000, sublinear_tf=True)
    char = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), min_df=3,
                           max_features=60000, sublinear_tf=True)
    wc = word.fit_transform(candidates.masked_text)
    wq = word.transform(queries.masked_text)
    cc = char.fit_transform(candidates.masked_text)
    cq = char.transform(queries.masked_text)
    records = pd.read_csv(ROOT / 'results/text/record_audit.csv', keep_default_na=False).set_index('row_id')
    edges = pd.read_csv(ROOT / 'results/kg/edges.csv', keep_default_na=False)
    cg = build_graph_features(records.loc[candidates.row_id].reset_index(), edges)
    qg = build_graph_features(records.loc[queries.row_id].reset_index(), edges)
    vectorizer = DictVectorizer()
    transformer = TfidfTransformer()
    gc = transformer.fit_transform(vectorizer.fit_transform(cg))
    gq = transformer.transform(vectorizer.transform(qg))
    weights = {'word': (1,0,0), 'character': (0,1,0), 'graph_idf': (0,0,1),
               'word_character': (.5,.5,0), 'word_graph': (.8,0,.2),
               'word_character_graph': (.4,.4,.2)}
    order = np.random.default_rng(42).permutation(len(candidates))

    def evaluate(frame, offset, methods):
        rankings = {name: [] for name in methods}
        for start in range(0, len(frame), 32):
            stop = min(start+32, len(frame))
            scores = [(q[offset+start:offset+stop] @ c.T).toarray()
                      for c,q in ((wc,wq),(cc,cq),(gc,gq))]
            for i, row in enumerate(frame.iloc[start:stop].itertuples()):
                eligible = (candidates.row_id.ne(row.row_id) & candidates.work_order.ne(row.work_order)
                            & candidates.template.ne(row.template)).to_numpy()
                pool = order[eligible[order]]
                for name in methods:
                    score = sum(weight * s[i] for weight,s in zip(weights[name], scores))
                    rankings[name].append(pool[np.argsort(-score[pool], kind='stable')][:50])
        return pd.concat([evaluate_rankings(rankings[name], frame, candidates, 'equipment_id', name)
                          for name in methods], ignore_index=True)

    dev = evaluate(development, 0, weights)
    dev.to_csv(out / 'development_per_query.csv', index=False)
    metrics = [c for c in dev.columns if c.startswith(('hit@', 'mrr@'))]
    means = dev.groupby('method')[metrics].mean()
    means.to_csv(out / 'development_metrics.csv')
    selected = means['mrr@50'].sort_values(ascending=False, kind='stable').index[0]
    write_json(out / 'locked_selection.json', {'selected': selected, 'weights': weights[selected],
        'selection_metric': 'mrr@50', 'confirmation_not_used_for_selection': True})
    test = evaluate(confirmation, len(development), list(dict.fromkeys(['word', selected])))
    test = pd.concat([test, random_expectation(confirmation, candidates)], ignore_index=True)
    test.to_csv(out / 'confirmation_per_query.csv', index=False)
    test.groupby('method')[metrics].mean().to_csv(out / 'confirmation_metrics.csv')
    if selected != 'word':
        paired_comparisons(test, ['hit@10','mrr@50'], [(selected,'word')]).to_csv(out / 'paired_differences.csv', index=False)
    raw = pd.read_csv(ROOT / 'results/text/record_audit.csv', keep_default_na=False)
    valid = raw.loc[raw.equipment_id.ne('')]
    write_json(out / 'target_audit.json', {
        'valid_records': len(valid),
        'identifier_concordance_fraction': float(valid.identifier_concordance.astype(str).str.lower().eq('true').mean()),
        'generator_url': 'https://github.com/jvachier/industrial-maintenance-synthetic-data/blob/main/src/generators/maintenance_generator.py',
        'generator_observation': 'Equipment_ID is mutated by iteration; copied description fields are not updated.',
        'caveat': 'Current upstream source is diagnostic evidence; frozen sample upstream revision is unknown.'})
    print('Development:\n', means.to_string(), flush=True)
    print('Selected:', selected, '\nConfirmation:\n', test.groupby('method')[metrics].mean().to_string(), flush=True)


if __name__ == '__main__':
    main()
