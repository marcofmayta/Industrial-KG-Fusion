import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import pandas as pd

from src.graph_quality import graph_quality_report
from src.temporal_lineage import temporal_lineage
from tools.result_history import snapshot_results,record_changes
from tools.research_audit import compare_frames


class ResearchAuditTests(unittest.TestCase):
    def graph(self):
        nodes=pd.DataFrame([dict(node_id='work_order:w',node_type='work_order',source_dataset='maintenance'),
            dict(node_id='equipment:P-01',node_type='equipment',source_dataset='maintenance')])
        edges=pd.DataFrame([dict(source='work_order:w',target='equipment:P-01',relation='ABOUT_EQUIPMENT',
            source_dataset='maintenance',provenance='structured field',evidence='P-01')])
        return nodes,edges

    def test_unknown_relation_and_wrong_domain_rejected(self):
        n,e=self.graph()
        self.assertTrue(graph_quality_report(n,e)[0]['passed'])
        e.loc[0,'relation']='INVENTED'
        self.assertEqual(graph_quality_report(n,e)[0]['checks']['unknown_relations'],1)
        e.loc[0,'relation']='HAS_SENSOR'
        self.assertEqual(graph_quality_report(n,e)[0]['checks']['invalid_domain_or_range'],1)

    def test_cross_source_identity_and_duplicate_nodes_rejected(self):
        n,e=self.graph()
        n.loc[1,'source_dataset']='metropt3'
        self.assertEqual(graph_quality_report(n,e)[0]['checks']['direct_cross_source_edges'],1)
        n=pd.concat([n,n.iloc[:1]],ignore_index=True)
        self.assertEqual(graph_quality_report(n,e)[0]['checks']['duplicate_node_ids'],1)

    def test_lexical_provenance_requires_spans(self):
        n,e=self.graph()
        e.loc[0,'provenance']='rule-based lexical extraction'
        self.assertEqual(graph_quality_report(n,e)[0]['checks']['invalid_lexical_provenance'],1)

    def temporal(self):
        events=pd.DataFrame([dict(event_id='SE_1',start='2020-01-01 00:00',end='2020-01-01 00:20',n_windows=2),
            dict(event_id='SE_2',start='2020-01-01 00:40',end='2020-01-01 00:45',n_windows=1)])
        windows=pd.DataFrame(dict(timestamp=pd.to_datetime(['2020-01-01 00:00','2020-01-01 00:05','2020-01-01 00:15','2020-01-01 00:40']),
                                 candidate=[True,False,True,True],n_obs=[1]*4,score=[2.]*4))
        return events,windows

    def test_merged_gaps_do_not_create_observations(self):
        e,w=self.temporal()
        membership,order=temporal_lineage(e,w,observations=w.timestamp)
        self.assertEqual(len(membership),3)
        self.assertNotIn(pd.Timestamp('2020-01-01 00:05'),set(membership.window_start))
        self.assertEqual(order.gap_minutes.tolist(),[20.])
        self.assertEqual(membership.observation_row_start.tolist(),[0,2,3])

    def test_overlaps_and_wrong_membership_fail(self):
        e,w=self.temporal()
        e.loc[1,'start']='2020-01-01 00:19'
        with self.assertRaises(ValueError):
            temporal_lineage(e,w)
        e,w=self.temporal(); e.loc[0,'n_windows']=3
        with self.assertRaises(ValueError):
            temporal_lineage(e,w)

    def test_saved_frame_comparison_detects_numeric_changes(self):
        a=pd.DataFrame(dict(method=['a','b'],score=[.1,.2]))
        self.assertTrue(compare_frames(a,a.iloc[::-1],['method']))
        b=a.copy(); b.loc[0,'score']=.11
        self.assertFalse(compare_frames(a,b,['method']))

    def test_result_history_preserves_original_values(self):
        import zipfile
        with TemporaryDirectory(prefix='industrial_kg_test_') as directory:
            root=Path(directory)
            (root/'results').mkdir(); (root/'src').mkdir(); (root/'tools').mkdir(); (root/'notebooks').mkdir()
            path=root/'results/metric.csv'; path.write_text('score\n0.1\n')
            original=path.read_bytes()
            snapshot=snapshot_results(root)
            path.write_text('score\n0.2\n')
            changes=record_changes(root,snapshot,'test recomputation')
            self.assertEqual(len(changes),1)
            with zipfile.ZipFile(snapshot[0]/'results.zip') as archive:
                self.assertEqual(archive.read('results/metric.csv'),original)
            self.assertIn('metric.csv',(root/'docs/RESULT_CHANGELOG.md').read_text())
