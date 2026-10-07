import itertools
import unittest

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix

from src.data import validate_equipment_id
from src.evaluation import expected_random_hit_probability, expected_random_mrr, evaluate_rankings, paired_comparisons
from src.config import ANALOG
from src.knowledge_graph import build_text_edges, build_text_nodes, build_sensor_branch, integrate_ontology, integration_checks
from src.retrieval import mask_identifiers, rank_candidates, build_graph_features
from src.sensor_events import fit_robust_baseline, score_sensor_points, merge_event_windows
from src.text_extraction import extract_entities, extract_asset_mentions


class MethodTests(unittest.TestCase):
    def test_identifier_validation_and_masking(self):
        for value in [None, "N/A", "NA", "NULL", "-", "NONE", "NaN", "FOR-2", "OVER-30", "P-001 junk", "P 001"]:
            self.assertEqual(validate_equipment_id(value), "")
        self.assertEqual(validate_equipment_id(" p-001 "), "P-001")
        text = mask_identifiers("P-102 ABC123 45.6 motor M/12 unit42 A_501")
        self.assertFalse(any(c.isdigit() for c in text))
        self.assertNotIn("abc", text)
        self.assertEqual(mask_identifiers("P-102 M/12 A_501"), "identifier identifier identifier")
        self.assertEqual(mask_identifiers("pump P-100, 30 bar"), mask_identifiers("pump P-999, 15 bar"))

    def test_regex_spans_and_false_assets(self):
        hits = extract_entities("centrifugal pump and gearbox", "equipment_type")
        self.assertEqual([h[0] for h in hits], ["centrifugal_pump", "gearbox"])
        self.assertEqual([x[0] for x in extract_asset_mentions("FOR-2 OVER-30 P-102 N/A SC-02")], ["P-102", "SC-02"])
        self.assertFalse(extract_asset_mentions("P-102-XYZ"))
        self.assertEqual(extract_entities("replace corroded gearbox", "failure_mode")[0][0], "corrosion")

    def test_random_expectation_exhaustively(self):
        for n in range(1, 7):
            for positives in range(n + 1):
                permutations = list(itertools.permutations(range(n)))
                for k in (0, 1, 3, 7):
                    hits, reciprocal = [], []
                    for order in permutations:
                        ranks = [i + 1 for i, item in enumerate(order[:k]) if item < positives]
                        hits.append(bool(ranks))
                        reciprocal.append(1 / ranks[0] if ranks else 0)
                    self.assertAlmostEqual(expected_random_hit_probability(n, positives, k), np.mean(hits))
                    self.assertAlmostEqual(expected_random_mrr(n, positives, k), np.mean(reciprocal))
        self.assertEqual(expected_random_hit_probability(0, 0, 10), 0)

    def test_exclude_before_ranking_and_target_independent_ties(self):
        candidates = pd.DataFrame({"row_id": [1, 2, 3, 4], "work_order": ["a", "b", "c", "d"],
                                   "template": ["same", "same", "other", "third"], "equipment_id": ["P-01"] * 4})
        queries = pd.DataFrame({"row_id": [1], "work_order": ["a"], "template": ["same"], "equipment_id": ["P-01"]})
        c, q = csr_matrix(np.ones((4, 1))), csr_matrix([[1]])
        rankings, hybrid, audit = rank_candidates([c, c], [q, q], candidates, queries, True)
        self.assertEqual(set(rankings[0][0]), {2, 3})
        self.assertEqual(set(hybrid[0]), {2, 3})
        self.assertEqual(audit.iloc[0].n_candidates, 2)
        candidates["equipment_id"] = ["A-01", "B-01", "C-01", "D-01"]
        repeated, _, _ = rank_candidates([c, c], [q, q], candidates, queries, True)
        np.testing.assert_array_equal(rankings[0][0], repeated[0][0])

    def test_graph_provenance_and_cross_source_guard(self):
        records = pd.DataFrame([dict(row_id=0, work_order="wo", equipment_id="P-01", order_type="CM", maintenance_type="CM01")])
        entities = pd.DataFrame([dict(row_id=0, work_order="wo", entity_type="equipment_type", entity_label="air_compressor",
                                     source_field="WorkOrderDescription", evidence="air compressor", span_start=0, span_end=14),
                                 dict(row_id=0, work_order="wo", entity_type="asset_mention", entity_label="P-01",
                                     source_field="WorkOrderDescription", evidence="P-01", span_start=15, span_end=19)])
        edges = build_text_edges(records, entities)
        nodes = build_text_nodes(records, edges)
        events = pd.DataFrame([dict(event_id="SE_1", start="2020-03-01", end="2020-03-02", duration_min=1440,
                                   score_max=2, peak_sensor="TP2", active_sensors="TP2")])
        sn, se = build_sensor_branch(events)
        all_nodes, all_edges = integrate_ontology(nodes, edges, sn, se)
        self.assertTrue(integration_checks(all_nodes, all_edges, events).passed.all())
        injected = pd.DataFrame([dict(source="equipment:P-01", target="sensor_asset:MetroPT3_APU", relation="UNKNOWN_RELATION",
                                      source_dataset="ontology", provenance="test", evidence="test")])
        checks = integration_checks(all_nodes, pd.concat([all_edges, injected]), events)
        self.assertFalse(checks.passed.all())
        features = build_graph_features(records, edges)
        self.assertFalse(any("P-01" in token for token in features[0]))

    def test_unknown_sensor_regime_fails(self):
        baseline = pd.DataFrame({"COMP": [0, 0, 0, 0], "TP2": [1, 1, 1, 1],
                                 "timestamp": pd.date_range("2020-02-01", periods=4, freq="10s")})
        stats = fit_robust_baseline(baseline, sensors=["TP2"])
        self.assertEqual(stats.iloc[0].scale_method, "constant")
        changed = baseline.copy()
        changed.loc[0, "TP2"] = 2
        points, _ = score_sensor_points(changed, stats, sensors=["TP2"])
        self.assertEqual(points.loc[0, "score"], 2)
        changed["COMP"] = 1
        with self.assertRaises(ValueError):
            score_sensor_points(changed, stats, sensors=["TP2"])

    def test_metrics_use_candidate_positions(self):
        queries = pd.DataFrame([dict(row_id=10, equipment_id="P-01")])
        candidates = pd.DataFrame({"equipment_id": ["P-02", "P-01", "P-03"]})
        result = evaluate_rankings([np.array([0, 1, 2])], queries, candidates, "equipment_id", "test")
        self.assertEqual(result.iloc[0]["hit@1"], 0)
        self.assertEqual(result.iloc[0]["hit@5"], 1)
        self.assertEqual(result.iloc[0]["mrr@10"], .5)

    def test_merge_gap_measured_from_window_end(self):
        windows = pd.DataFrame(index=pd.to_datetime(["2020-03-01 00:00", "2020-03-01 00:15", "2020-03-01 00:31"]))
        windows["candidate"] = True
        windows["score"] = 2
        for sensor in ANALOG:
            windows[f"{sensor}_max"] = 2
        events = merge_event_windows(windows, freq="5min", gap_minutes=10)
        self.assertEqual(events.n_windows.tolist(), [2, 1])
        self.assertEqual(events.duration_min.tolist(), [20, 5])

    def test_paired_bootstrap_aligns_queries(self):
        first = pd.DataFrame({"method": ["a"] * 3, "query_id": [3, 1, 2],
                              "equipment_id": ["P-01", "P-02", "P-01"], "hit@10": [1., 0., 1.]})
        second = first.iloc[::-1].copy()
        second["method"] = "b"
        differences = paired_comparisons(pd.concat([first, second]), ["hit@10"], [("a", "b")])
        self.assertEqual(differences.iloc[0]["difference"], 0)
        self.assertEqual(differences.iloc[0]["ci95_low"], 0)
        self.assertEqual(differences.iloc[0]["ci95_high"], 0)


if __name__ == "__main__":
    unittest.main()
