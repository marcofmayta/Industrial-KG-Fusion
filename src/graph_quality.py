
import json
from pathlib import Path
import networkx as nx
import pandas as pd


def load_schema(path=None):
    path = Path(path) if path else Path(__file__).resolve().parents[1] / 'config/kg_schema.json'
    return json.loads(path.read_text(encoding='utf-8'))


def graph_quality_report(nodes, edges, schema=None):
    schema = load_schema() if schema is None else schema
    checks = {}
    checks['duplicate_node_ids'] = int(nodes.node_id.duplicated().sum())
    checks['duplicate_complete_edges'] = int(edges.duplicated().sum())
    checks['invalid_node_types'] = int((~nodes.node_type.isin(schema['node_types'])).sum())
    checks['invalid_node_sources'] = int((~nodes.source_dataset.isin(schema['source_datasets'])).sum())
    checks['invalid_edge_sources'] = int((~edges.source_dataset.isin(schema['source_datasets'])).sum())
    lookup = nodes.drop_duplicates('node_id').set_index('node_id')
    source_types, target_types = edges.source.map(lookup.node_type), edges.target.map(lookup.node_type)
    checks['missing_endpoints'] = int((source_types.isna() | target_types.isna()).sum())
    checks['unknown_relations'] = int((~edges.relation.isin(schema['relations'])).sum())
    checks['forbidden_relations'] = int(edges.relation.isin(schema['forbidden_relations']).sum())
    bad_domain = pd.Series(False, index=edges.index)
    for relation, definition in schema['relations'].items():
        selected = edges.relation.eq(relation)
        bad_domain |= selected & (~source_types.isin(definition['domain']) | ~target_types.isin(definition['range']))
    checks['invalid_domain_or_range'] = int(bad_domain.sum())
    a, b = schema['forbidden_direct_dataset_pair']
    left, right = edges.source.map(lookup.source_dataset), edges.target.map(lookup.source_dataset)
    checks['direct_cross_source_edges'] = int(((left.eq(a) & right.eq(b)) | (left.eq(b) & right.eq(a))).sum())
    checks['self_loops'] = int(edges.source.eq(edges.target).sum())
    fields = schema['required_edge_metadata']
    checks['missing_edge_provenance'] = int((edges[fields].isna() | edges[fields].eq('')).any(axis=1).sum())
    origins = edges.provenance.map(schema['provenance_origins'])
    checks['unclassified_origins'] = int(origins.isna().sum())
    lexical = origins.eq('lexical_extraction')
    required = ['row_id', 'source_field', 'span_start', 'span_end']
    if lexical.any() and not set(required).issubset(edges):
        checks['invalid_lexical_provenance'] = int(lexical.sum())
    elif lexical.any():
        selected = edges.loc[lexical]
        start = pd.to_numeric(selected.span_start, errors='coerce')
        end = pd.to_numeric(selected.span_end, errors='coerce')
        row = pd.to_numeric(selected.row_id, errors='coerce')
        bad = start.isna() | end.isna() | row.isna() | start.lt(0) | end.le(start) | start.mod(1).ne(0) | end.mod(1).ne(0) | row.mod(1).ne(0)
        bad |= ~selected.source_field.isin(['WorkOrderDescription', 'OperationDescription'])
        checks['invalid_lexical_provenance'] = int(bad.sum())
    else:
        checks['invalid_lexical_provenance'] = 0
    temporal = nodes.loc[nodes.node_type.eq('sensor_event')]
    if len(temporal) and not {'start', 'end', 'duration_min'}.issubset(temporal):
        checks['invalid_event_intervals'] = len(temporal)
    elif len(temporal):
        start, end = pd.to_datetime(temporal.start, errors='coerce'), pd.to_datetime(temporal.end, errors='coerce')
        duration = pd.to_numeric(temporal.duration_min, errors='coerce')
        checks['invalid_event_intervals'] = int((start.isna() | end.isna() | end.le(start) | duration.isna() | ((end-start).dt.total_seconds()/60-duration).abs().gt(1e-8)).sum())
    else:
        checks['invalid_event_intervals'] = 0
    graph = nx.Graph()
    graph.add_nodes_from(nodes.node_id)
    graph.add_edges_from(edges[['source', 'target']].itertuples(index=False, name=None))
    components = sorted((len(c) for c in nx.connected_components(graph)), reverse=True)
    degree = pd.Series(dict(graph.degree()))
    provenance = edges.assign(relation_origin=origins.fillna('unclassified')).groupby(['source_dataset', 'provenance', 'relation_origin']).size().reset_index(name='edges')
    return {'schema_version': schema['schema_version'], 'nodes': len(nodes), 'edges': len(edges),
        'checks': checks, 'passed': all(v == 0 for v in checks.values()),
        'structure': {'orphan_nodes': int(degree.eq(0).sum()), 'connected_components': len(components),
            'component_sizes': components, 'maximum_undirected_degree': int(degree.max()) if len(degree) else 0,
            'repeated_triples_with_distinct_metadata': int(edges.duplicated(['source', 'relation', 'target']).sum())},
        'interpretation': 'Connectivity and repeated triples can reflect shared vocabulary and separate source evidence, not physical topology.'}, provenance
