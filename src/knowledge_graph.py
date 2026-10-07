from urllib.parse import quote, unquote

import networkx as nx
import pandas as pd

from .config import ANALOG, DIGITAL

RELATIONS = {
    "equipment_type": "MENTIONS_EQUIPMENT_TYPE",
    "failure_mode": "REPORTS_FAILURE_MODE",
    "component": "INVOLVES_COMPONENT",
    "maintenance_action": "HAS_MAINTENANCE_ACTION",
    "asset_mention": "MENTIONS_ASSET_TOKEN",
}


def node_id(kind, label):
    return f"{kind}:{quote(str(label), safe='_-')}"


def build_text_edges(records, entities):
    rows = []
    structured = [("equipment_id", "ABOUT_EQUIPMENT", "equipment", "Equipment_ID"),
                  ("order_type", "HAS_ORDER_TYPE", "order_type", "OrderType"),
                  ("maintenance_type", "HAS_MAINTENANCE_TYPE", "maintenance_type", "Maintenance_activity_type")]
    for row in records.itertuples(index=False):
        for attr, relation, kind, field in structured:
            value = getattr(row, attr)
            if value:
                rows.append(dict(source=node_id("work_order", row.work_order), relation=relation,
                                 target=node_id(kind, value), row_id=row.row_id, source_field=field,
                                 evidence=value, source_dataset="maintenance", provenance="structured field",
                                 certainty="observed field; not independently verified"))
    for row in entities.itertuples(index=False):
        rows.append(dict(source=node_id("work_order", row.work_order), relation=RELATIONS[row.entity_type],
                         target=node_id(row.entity_type, row.entity_label), row_id=row.row_id,
                         source_field=row.source_field, evidence=row.evidence,
                         source_dataset="maintenance", provenance="rule-based lexical extraction",
                         certainty="lexical mention; not confirmed condition",
                         span_start=row.span_start, span_end=row.span_end))
    return pd.DataFrame(rows).drop_duplicates().reset_index(drop=True)


def build_text_nodes(records, edges):
    identifiers = sorted(set(edges["source"]) | set(edges["target"]) |
                         {node_id("work_order", w) for w in records["work_order"]})
    return pd.DataFrame([dict(node_id=i, node_type=i.split(":", 1)[0],
                              label=unquote(i.split(":", 1)[1]), source_dataset="maintenance")
                         for i in identifiers])


def to_graph(nodes, edges):
    graph = nx.MultiDiGraph()
    for row in nodes.to_dict("records"):
        identifier = row.pop("node_id")
        graph.add_node(identifier, **{k: v for k, v in row.items() if pd.notna(v)})
    for index, row in enumerate(edges.to_dict("records")):
        source, target = row.pop("source"), row.pop("target")
        graph.add_edge(source, target, key=index, **{k: v for k, v in row.items() if pd.notna(v)})
    return graph


def graph_statistics(nodes, edges):
    graph = nx.Graph()
    graph.add_nodes_from(nodes["node_id"])
    graph.add_edges_from(edges[["source", "target"]].itertuples(index=False, name=None))
    components = sorted((len(c) for c in nx.connected_components(graph)), reverse=True)
    degree = pd.DataFrame(graph.degree(), columns=["node_id", "degree"])
    degree = degree.merge(nodes[["node_id", "node_type", "label"]], on="node_id", validate="one_to_one")
    summary = dict(nodes=len(nodes), edges=len(edges), connected_components=len(components),
                   largest_component=components[0] if components else 0,
                   median_degree=float(degree["degree"].median()),
                   max_degree=int(degree["degree"].max()))
    return summary, degree.sort_values(["degree", "node_id"], ascending=[False, True])


def build_sensor_branch(events):
    asset = "sensor_asset:MetroPT3_APU"
    nodes = [dict(node_id=asset, node_type="sensor_asset", label="MetroPT-3 APU", source_dataset="metropt3"),
             dict(node_id="source_dataset:metropt3", node_type="source_dataset", label="MetroPT-3", source_dataset="metropt3")]
    edges = []

    def add(source, relation, target, evidence, provenance="sensor schema", dataset="metropt3"):
        edges.append(dict(source=source, relation=relation, target=target,
                          source_dataset=dataset, provenance=provenance, evidence=str(evidence)))

    add(asset, "DERIVED_FROM", "source_dataset:metropt3", "UCI dataset 791", "dataset metadata")
    for sensor in (*ANALOG, *DIGITAL):
        family = ("pressure" if sensor in ANALOG[:5] else "temperature" if sensor == "Oil_temperature"
                  else "electrical" if sensor == "Motor_current" else "digital_control")
        nodes.extend([dict(node_id=f"sensor:{sensor}", node_type="sensor", label=sensor, source_dataset="metropt3"),
                      dict(node_id=f"sensor_family:{family}", node_type="sensor_family", label=family, source_dataset="ontology")])
        add(asset, "HAS_SENSOR", f"sensor:{sensor}", sensor)
        add(f"sensor:{sensor}", "HAS_SENSOR_FAMILY", f"sensor_family:{family}", family, "manual sensor taxonomy", "ontology")
    for row in events.itertuples(index=False):
        event = f"sensor_event:{row.event_id}"
        nodes.append(dict(node_id=event, node_type="sensor_event", label=row.event_id,
                          source_dataset="metropt3", start=str(row.start), end=str(row.end),
                          duration_min=row.duration_min, score=row.score_max))
        add(event, "OBSERVED_ON", asset, row.event_id, "results/sensor/events.csv")
        add(event, "PEAK_SENSOR", f"sensor:{row.peak_sensor}", row.peak_sensor, "results/sensor/events.csv")
        for sensor in str(row.active_sensors).split("|"):
            if sensor in ANALOG:
                add(event, "INVOLVES_SENSOR", f"sensor:{sensor}", sensor, "results/sensor/events.csv")
    return pd.DataFrame(nodes).drop_duplicates("node_id"), pd.DataFrame(edges)


def integrate_ontology(text_nodes, text_edges, sensor_nodes, sensor_edges):
    types = text_nodes.loc[text_nodes["node_type"].eq("equipment_type")]
    rows, links = [], []
    for row in types.itertuples(index=False):
        concept = node_id("concept", row.label)
        rows.append(dict(node_id=concept, node_type="concept", label=row.label, source_dataset="ontology"))
        links.append(dict(source=row.node_id, relation="DENOTES", target=concept,
                          source_dataset="ontology", provenance="manual industrial class mapping", evidence=row.label))
    for specific, parent in [("air_compressor", "compressor"), ("centrifugal_pump", "pump"),
                             ("electric_motor", "motor"), ("screw_conveyor", "conveyor")]:
        for label in (specific, parent):
            rows.append(dict(node_id=node_id("concept", label), node_type="concept", label=label, source_dataset="ontology"))
        links.append(dict(source=node_id("concept", specific), relation="SUBCLASS_OF", target=node_id("concept", parent),
                          source_dataset="ontology", provenance="manual industrial class hierarchy", evidence=f"{specific} is a {parent}"))
    links.append(dict(source="sensor_asset:MetroPT3_APU", relation="INSTANCE_OF", target="concept:compressor",
                      source_dataset="metropt3", provenance="UCI dataset metadata", evidence="Air compressor APU"))
    source_node = pd.DataFrame([dict(node_id="source_dataset:maintenance", node_type="source_dataset",
                                     label="Industrial maintenance synthetic", source_dataset="maintenance")])
    work_orders = text_nodes.loc[text_nodes["node_type"].eq("work_order"), "node_id"]
    membership = pd.DataFrame(dict(source=work_orders, relation="DERIVED_FROM", target="source_dataset:maintenance",
                                   source_dataset="maintenance", provenance="dataset membership", evidence="maintenance work order"))
    nodes = pd.concat([text_nodes, sensor_nodes, source_node, pd.DataFrame(rows)], ignore_index=True).drop_duplicates("node_id")
    edges = pd.concat([text_edges, sensor_edges, membership, pd.DataFrame(links)], ignore_index=True)
    return nodes.reset_index(drop=True), edges.reset_index(drop=True)


def integration_checks(nodes, edges, events):
    sources = nodes.set_index("node_id")["source_dataset"]
    left, right = edges["source"].map(sources), edges["target"].map(sources)
    cross = ((left.eq("metropt3") & right.eq("maintenance")) |
             (left.eq("maintenance") & right.eq("metropt3")))
    bridge = nx.DiGraph()
    bridge.add_edges_from(edges.loc[edges["relation"].isin(["DENOTES", "SUBCLASS_OF"]), ["source", "target"]].itertuples(index=False, name=None))
    text_bridge = any(nx.has_path(bridge, i, "concept:compressor") for i in nodes.loc[nodes["node_type"].eq("equipment_type"), "node_id"] if i in bridge)
    instance = ((edges["source"] == "sensor_asset:MetroPT3_APU") &
                (edges["target"] == "concept:compressor") & (edges["relation"] == "INSTANCE_OF")).any()
    checks = {
        "sensor events loaded": nodes["node_type"].eq("sensor_event").sum() == len(events),
        "text KG loaded": nodes["node_type"].eq("work_order").any(),
        "ontology bridge exists": text_bridge and instance,
        "no direct cross-dataset edges in either direction": not cross.any(),
        "no identity relations": not edges["relation"].isin(["SAME_AS", "IDENTICAL_TO"]).any(),
        "every edge has provenance and evidence": edges[["provenance", "evidence", "source_dataset"]].notna().all().all() and edges[["provenance", "evidence", "source_dataset"]].ne("").all().all(),
        "all endpoints exist": left.notna().all() and right.notna().all(),
    }
    return pd.DataFrame([dict(check=k, passed=bool(v)) for k, v in checks.items()])
