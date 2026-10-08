# Knowledge graph schema and temporal semantics

The implemented representation is a directed property multigraph. [Machine-readable schema](../config/kg_schema.json) validates types, relation domain/range, source namespaces and prohibited identities. It is a lightweight schema, not a formally verified industrial ontology. No numerical extraction confidence is calibrated.

## Nodes

| Namespace/type | Meaning | Source and limits |
| --- | --- | --- |
| work_order | Source WorkOrder value, with evidence from all retained rows | Synthetic maintenance; conflicting field values are preserved with row provenance |
| equipment | Syntactically validated structured Equipment_ID | Not verified physical equipment identity |
| equipment_type, component, failure_mode, maintenance_action | Shared lexical category nodes | Mentions, not certified installed components, failures or recommended actions |
| asset_mention | Code mentioned in text | Not automatically identical to structured equipment |
| order_type, maintenance_type | Structured categorical values | Source fields may contain synthetic impurities |
| sensor_asset | MetroPT compressor APU | A real source-specific asset, unrelated to synthetic maintenance equipment |
| sensor | One of 15 recorded channels | Sensor schema, not inferred plant topology |
| sensor_event | Deterministically merged anomalous candidate windows | Interval and score are computed features, not confirmed faults |
| sensor_family, concept | Manual taxonomy and industrial classes | Conceptual organization only |
| source_dataset | Dataset membership | Source-level provenance |

## Relation origins

| Category | Relations/examples | What the evidence supports |
| --- | --- | --- |
| A. Directly supported source fields/metadata | ABOUT_EQUIPMENT, HAS_ORDER_TYPE, HAS_MAINTENANCE_TYPE, HAS_SENSOR, APU INSTANCE_OF compressor | Existence of a field or documented dataset channel/class; not externally confirmed identity |
| B. Extracted from text | MENTIONS_EQUIPMENT_TYPE, REPORTS_FAILURE_MODE, INVOLVES_COMPONENT, HAS_MAINTENANCE_ACTION, MENTIONS_ASSET_TOKEN | A lexical match at a recorded span in a cleaned field; not causal diagnosis or an operational recommendation |
| C. Deterministic construction | DERIVED_FROM membership, OBSERVED_ON, PEAK_SENSOR, INVOLVES_SENSOR; temporal sidecar PRECEDES | Dataset membership, calibrated-window aggregation and event ordering, not independent ground truth |
| D. Conceptual organization | DENOTES, SUBCLASS_OF, HAS_SENSOR_FAMILY | Manual class/taxonomy mappings; no observed cross-source physical relation |
| E. Requires industrial mapping | SAME_AS between sources, installed HAS_COMPONENT, intervention causality | Not implemented. Requires shared source-supported identity and independent verification |

Existing edges retain source_dataset, provenance, evidence and, where available, row_id/source_field and spans. Offsets refer to cleaned problem/action strings in `results/text/record_audit.csv`, not raw uncleaned text. Nodes retain source namespace; work-order node identity does not preserve row individuality by itself, so edge row provenance is essential. [Provenance summary](../results/kg/provenance_summary.csv) classifies original strings without rewriting edges. Source hashes are recorded in manifests and audit reports; no invented per-edge confidence is added.

## Temporal extension

`results/temporal/event_window_membership.csv` links each observed candidate window to exactly one event. It references `results/sensor/window_scores.parquet`; when the sorted processed sensor dataset is available, zero-based half-open observation row ranges identify the relevant source rows. The valid-observation count can be smaller than the row range when measurements are incomplete.

Events and windows use `[start,end)`. Event duration includes permitted merged gaps; gaps are **not** inserted as candidate observations. Timestamps are source-local and timezone-unspecified. `event_order.csv` contains immediate adjacency between consecutive nonoverlapping event intervals. PRECEDES states order, never causation. These are separate derived facts; the original graph remains at 61278 nodes and 621865 edges.

This PoC supports temporal event intervals, observation lineage and chronological queries. It does not implement temporal embeddings, evolving maintenance links, interval-based causal inference, prediction of interventions, or temporal graph learning. Synthetic maintenance date corruption prevents reliable cross-source temporal alignment.

## Quality checks

[Graph quality report](../results/graph_quality_report.json) covers duplicate IDs/complete edges, invalid types/sources/relations/domain/range, missing endpoints/provenance, unknown origins, invalid lexical spans, forbidden identities, self-loops and malformed event intervals. Orphans, connected components, repeated triples and maximum undirected degree are descriptive diagnostics. A giant component or generic hub is not a physical equipment network. Passing structural checks does not validate extraction accuracy or industrial usefulness.
