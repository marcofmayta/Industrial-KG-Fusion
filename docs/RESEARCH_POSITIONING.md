# Research positioning

## What the public-data PoC establishes

The repository demonstrates text preprocessing with evidence spans, structured-field auditing, rule-based entity/relation construction, temporal sensor event extraction, a provenance-bearing property graph, schema checks and controlled retrieval comparisons. Code and saved artifacts expose the development from an easy diagnostic task to a harder structured target and a subsequent unsuccessful optimization. This is preliminary technical evidence, not an industrial deployment.

The principal question is:

> When does structured graph context provide measurable information beyond strong text and temporal baselines in heterogeneous industrial information systems?

The present evidence does not answer it generally. Text and one-hop entity features exceed random retrieval for synthetic asset labels, but graph and equal-weight RRF do not outperform the stronger text baseline. A large relative lift coexists with low absolute Hit@10. The graph-feature experiment does not train embeddings, a GNN or a temporal graph model. No claim of methodological novelty is made without a literature comparison.

## Evidence boundaries

The [README](../README.md#limitations) summarizes the essential limitations; [result traceability](RESULT_TRACEABILITY.md) retains complete evidence and hypotheses. The current result does not establish physical integration, independent technical relevance or industrial benefit.

## Remaining methodological gaps

The fixed maintenance snapshot lacks a known upstream revision and is not publicly included in Git. Structured asset labels have extensive textual disagreement. Diagnostic failure labels derive from the evaluated text. Query/candidate cohort construction and group overlap are documented, but primary retrieval remains a known-synthetic-asset task conditioned on a fixed sample and seed. Multiple comparisons are unadjusted. The review pilot has only 40 queries and no completed expert annotation. Problem-only query graph versus problem+action candidate graph is an asymmetric retrieval setting; it should not be interpreted as a symmetric graph benchmark. Combined-template exclusion does not remove every repeated problem template.

Feature availability is not identical across methods: the full graph context includes structured order/maintenance categories, whereas text uses masked descriptions. Candidate graph vectors also include action context absent from problem-only query vectors. These are disclosed experimental settings, not a definitive feature-matched test of graph structure. Future ablations should equalize information and distinguish extra fields from relational value.

## What company data would change

Only authorized, governed industrial data could establish machine/component identity, installed topology, timestamps/timezones, document versions, sensor channels, intervention histories and access rights. It would permit source-supported entity resolution and temporal association, with uncertainty and evidence attached to each mapping. It would not automatically justify a causal link or prove that graph structure improves retrieval. Identity resolution, temporal availability and label construction must be evaluated independently.

## Next experiments

1. Establish problem-level template controls and adjudicated relevance before tuning. Compare text, character retrieval, graph context and hybrids on the same eligible pool; include confidence intervals and analysis by missing feature coverage.
2. Freeze development choices and evaluate on a new temporal/source holdout. Assess several predetermined seeds and predefine primary metrics and multiplicity handling.
3. Test controlled missing/noisy text to assess whether structured graph context offers incremental robustness. These are proposals, not completed results; lexical labels cannot validate this hypothesis.
4. With industrial identity available, compare text-only and text+temporal baselines before claiming KG value. Preserve sensor/time features with identical availability cutoffs and check that interventions written after an event never enter its query representation.
5. Consider graph learning only after a nontrivial, independently labelled task and evidence that relational paths matter. Compare against equally informed tabular/lexical baselines, including relation ablations and cost.

The integration challenge is jointly about text meaning, temporal availability, physical identity, provenance and graph structure. More nodes or a visually connected graph alone do not address it.
