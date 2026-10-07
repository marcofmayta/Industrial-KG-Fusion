import unittest
import pandas as pd
from tools.evaluate_independent_review import evaluate, validate_against_template


class ReviewTests(unittest.TestCase):
    def fixture(self):
        key = pd.DataFrame(dict(pair_id=[str(i) for i in range(10)], method=['text']*10,
                                query_id=[1]*10, rank=list(range(1,11))))
        labels = pd.DataFrame(dict(pair_id=[str(i) for i in range(10)], relevance=[3]+[0]*9,
            unsafe=['no']*10, reviewer=['expert']*10, review_split=['confirmation']*10))
        return labels,key

    def test_pending_and_duplicate_annotations_rejected(self):
        labels,key = self.fixture()
        labels.loc[0,'relevance'] = float('nan')
        with self.assertRaises(ValueError):
            evaluate(labels,key)
        labels,key = self.fixture()
        with self.assertRaises(ValueError):
            evaluate(pd.concat([labels,labels.iloc[:1]]),key)

    def test_known_ranking_and_safety(self):
        labels,key = self.fixture()
        labels.loc[0,'unsafe'] = 'yes'
        result = evaluate(labels,key).iloc[0]
        self.assertEqual(result.precision_at_10,.1)
        self.assertEqual(result.pooled_ndcg_at_10,1.)
        self.assertEqual(result.unsafe_fraction,.1)

    def test_review_split_and_pair_metadata_cannot_be_changed(self):
        labels,_ = self.fixture()
        labels['query_id'] = 7
        template = labels.copy()
        self.assertEqual(len(validate_against_template(labels,template)),10)
        labels.loc[0,'review_split'] = 'development'
        with self.assertRaises(ValueError):
            validate_against_template(labels,template)
        labels = template.copy()
        labels.loc[0,'query_id'] = 99
        with self.assertRaises(ValueError):
            validate_against_template(labels,template)


if __name__ == '__main__':
    unittest.main()
