# Result changelog

## Graph validation and temporal lineage

Hashes of 77 scientific files are recorded in `docs/audit_baseline.json`; historical comparison is recorded in `results/audit_preservation.json`. Retrieval metrics, intervals, lifts, event counts and original graph counts are unchanged.

| Result | Old value | New value | Reason and responsible code |
| --- | --- | --- | --- |
| Original graph | 61278 nodes, 621865 edges | Unchanged | `src/graph_quality.py` validates the original files without rewriting them |
| Original sensor events and candidate windows | 2934 events, 9472 candidate windows | Unchanged | `src/temporal_lineage.py` constructs additive provenance |
| Event-window membership | Not exported | 9472 membership rows | `src/temporal_lineage.py`, `tools/research_audit.py`; only actually observed candidate windows |
| Immediate chronological adjacency | Not exported | 2933 PRECEDES rows | Same modules; separate sidecar, not original graph edges and not causality |
| Methodological tests | 15 passing tests | 22 passing tests | Seven additional tests cover schema, temporal lineage, result preservation and numeric verification |

New additive reports: graph quality, provenance categories, temporal lineage and saved-result verification. Their creation is not evidence that retrieval performance improved. No original rank experiment was rerun or selected to obtain a favorable outcome.

Future runner executions append a ledger entry after preserving old values in an ignored local ZIP, including partial runs. Each changed file has old/new hashes, source locations for exact old/new values, a reason and responsible code hashes. Distributing a changed experiment also requires distributing its history deliberately; a local ignored archive alone is not public reproducibility.

## 20261008T022014834932Z

Reason: Pipeline execution; original result files preserved before computation, including partial runs

Previous values and manifest: `archive/runs/20261008T022014834932Z`. This local archive is excluded from Git.

No previous result artifact changed.

## Retired lexical relevance screening

The non-independent lexical relevance screening experiment was removed from the active pipeline and public results. Its five output files, implementation and three dedicated tests were retired; the previous values remain in the pre-execution archive under `archive/runs/`. Historical hashes are retained without representing the retired files as current outputs.

No human relevance labels replace the screening. Independent review remains pending, and the confirmation pool remains previously inspected. The active suite now contains 19 methodological tests; saved-result verification contains 21 local checks when both raw and processed inputs are available. Remaining experiment metrics are unchanged.
