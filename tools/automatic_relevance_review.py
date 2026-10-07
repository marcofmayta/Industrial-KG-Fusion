"""Conservative lexical screening; these labels are not independent ground truth."""
from pathlib import Path
import sys
import re
from difflib import SequenceMatcher
import unicodedata
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data import write_json
from src.retrieval import mask_identifiers
from tools.evaluate_independent_review import evaluate


def normalized(text):
    return mask_identifiers(unicodedata.normalize('NFKC', str(text)))


def screen_pair(problem, candidate, action):
    q, c = normalized(problem), normalized(candidate)
    similarity = SequenceMatcher(None, q, c, autojunk=False).ratio()
    qids = re.findall(r'\b([A-Z]{1,6})-\d', problem)
    cids = re.findall(r'\b([A-Z]{1,6})-\d', candidate)
    same_family = bool(qids and cids and qids[0] == cids[0])
    if qids and cids and qids[0] != cids[0]:
        grade, reason = 0, 'Different equipment-code families; compatibility not established.'
    elif not str(action).strip():
        grade = 1 if same_family and similarity >= .5 else 0
        reason = 'No intervention provided; cannot establish actionable usefulness.'
    elif same_family and similarity >= .9:
        grade, reason = 2, 'Same equipment-code family and near-identical problem; possible useful precedent requiring verification.'
    elif same_family and similarity >= .5:
        grade, reason = 1, 'Related equipment family and partial problem similarity; intervention suitability unverified.'
    else:
        grade, reason = 0, 'Insufficient observable compatibility under the fixed screening rule.'
    return grade, similarity, reason


def main():
    out = ROOT / 'results/automatic_review'
    out.mkdir(parents=True, exist_ok=True)
    pairs = pd.read_csv(ROOT / 'results/independent_review/blinded_pairs.csv', keep_default_na=False)
    rows = []
    for row in pairs.itertuples():
        grade, similarity, reason = screen_pair(row.query_problem, row.candidate_problem, row.candidate_action)
        item = row._asdict()
        item.pop('Index')
        item.update(relevance=grade, unsafe='uncertain', reviewer='automatic_lexical_screen_v1',
                    rationale=reason, problem_similarity=similarity, annotation_source='automatic_rule')
        rows.append(item)
    labels = pd.DataFrame(rows)
    labels.to_csv(out / 'screened_pairs.csv', index=False)
    key = pd.read_csv(ROOT / 'results/independent_review/ranking_key_do_not_show_reviewers.csv')
    metrics = evaluate(labels, key)
    metrics.to_csv(out / 'screen_per_query.csv', index=False)
    means = metrics.groupby(['review_split','method'])[['precision_at_10','pooled_ndcg_at_10','uncertain_fraction']].mean()
    means.to_csv(out / 'screen_metrics.csv')
    write_json(out / 'protocol.json', dict(status='exploratory_automatic_screen_only', pairs=len(labels),
        labels_independent=False, evidence_level='laboratory research prototype using synthetic maintenance records',
        thresholds={'near_identical':.9,'partially_related':.5},
        grade_3_never_assigned=True, safety_assessment='all uncertain; no safety validation performed',
        limitations=['Lexical agreement cannot validate retrieval and can favor lexical methods.',
          'Equipment prefixes are descriptive proxies, not validated physical identities.',
          'No human annotation, external validation, diagnosis or industrial benefit established.',
          'Development and confirmation are reported separately; no tuning or winner selection from these labels.']))
    print('Screened pairs:', len(labels))
    print('Missing candidate interventions:', int(labels.candidate_action.eq('').sum()))
    print(means.to_string())


if __name__ == '__main__':
    main()
