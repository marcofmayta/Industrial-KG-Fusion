# Result traceability

The chain is **source data → implementing computation → saved artifact → reporting claim**. READMEs in all five languages share the main result table. Detailed tables, hypotheses and interpretations are retained below. Verification refers to saved artifacts unless explicitly stated otherwise; it is not an independent validation of semantics.

The verification column distinguishes saved-artifact checks from complete execution. Execution scope is documented in [REPRODUCIBILITY.md](REPRODUCIBILITY.md).

| Result | Source | Computation | Artifact | Reproducible? | Notes |
| --- | --- | --- | --- | --- | --- |
| 1516948 sensor observations, 15 channels, median 10-second interval | Fixed MetroPT CSV | `src.data.load_metropt`; notebook 00 structure audit | `results/data_audit.csv`, `results/data_manifest.json` | Locally, exact input hash verified | CSV excluded from Git; public download exists |
| 50000 maintenance records | Frozen maintenance Parquet | `src.data.load_maintenance`; notebook 00 | `results/data_manifest.json`, snapshot hashes | Locally; not from fresh clone without snapshot | Upstream revision unknown |
| 1150 removed duplicates, 48850 retained records, 410689 mentions, 9400 syntactically valid asset values | Deduplicated maintenance sample | `src.text_extraction.extract_records`; notebook 02 | `results/text/summary.json`, records/entities/duplicate CSVs | Counts recomputed from saved CSVs | No extraction precision estimate |
| Coverage of five entity families | Entity counts per retained record | Notebook 02 `n_kind > 0` | `results/text/extraction_coverage.csv` | Recomputed exactly | Coverage is not correctness |
| 2934 events; 9472/41042 windows, 23.079 % candidate fraction | Sensor readings; February baseline | `src.sensor_events`; notebook 01 fixed calibration and merging | `results/sensor/events.csv`, `window_scores.parquet`, `summary.json` | Event counts/fraction verified; lineage regenerated | Full detection not rerun in this audit |
| Four of four official failure periods overlap | Events and official periods recorded in notebook 01 | Strict interval-overlap rule | `results/sensor/failure_overlap.csv` | Saved indicators/counts checked | Not validated lead time or specificity |
| 789.333 observed candidate hours; 1110.333 event-span hours | Window frequency, candidates, event duration | Notebook 01 duration formulas | `results/sensor/summary.json` | Derived from artifacts | Merged gaps are included only in span duration |
| Text graph 58311 nodes, 554016 edges and one connected component | Record audit and entity CSVs | `src.knowledge_graph.build_text_*`, `graph_statistics`; notebook 03 | `results/kg/text/summary.json`, nodes/edges/degrees | Artifacts available locally; counts verified during inventory | Generic lexical hubs, not physical topology |
| Integrated graph 61278 nodes, 621865 edges; 7/7 original integration checks | Text branch, sensor events and class mappings | `integrate_ontology`, `integration_checks`; notebook 04 | `results/kg/summary.json`, `integration_checks.csv` | Full graph quality reread against schema | Conceptual integration only; no ROMI data |
| Diagnostic retrieval tables, including near-100 % values | Text-derived failure labels and group splits | Notebook 05; `src.retrieval`, `src.evaluation` | `results/retrieval/diagnostic/{metrics,per_query,split_audit,findings}.csv/json` | Means recomputed exactly | Circular/diagnostic labels; not independent accuracy |
| Asset cohort 38534 records, 5128 assets; 37034 candidates, 1500 queries, 1246 query assets; 10 conflicting work orders | Structured field audit and cohort restrictions | Notebook 06 cohort and disjoint-index construction | `results/retrieval/asset/summary.json`, cohorts/queries | Saved CSV counts and hashes available | Known synthetic asset task |
| Asset Hit@1/5/10/20/50 and MRR@10/50 for five methods | Candidate-fitted representations and full eligible rankings | Notebook 06; `rank_candidates`, `evaluate_rankings`, exact random expectation | `results/retrieval/asset/metrics.csv`, `per_query.csv` | All means recomputed exactly | Rankings not rerun; raw labels not verified physical identity |
| 35 asset CI rows; 28 paired-difference rows; 28 lift rows | Same per-query scores | `bootstrap_ci`, `paired_comparisons`, `lift_intervals` | `confidence_intervals.csv`, `paired_differences.csv`, `lift.csv` | Exactly recomputed, 500 resamples, seed 42 | Unadjusted multiplicity, fixed sample/index |
| Graph Hit@10 2.267 %, text/hybrid 3.333 %, random 0.221 %; text lift 15.055839 | Asset experiment above | Group means and matched random lift | Same asset metric/lift tables → all READMEs | Verified, with rounding | Large lift does not prove practical usefulness |
| Optimization six development methods and two confirmation methods plus random | Old exposed queries for development; 1500 new reserved rows, seed 314159 | `tools/improve_retrieval.py`; notebook 07 | `results/retrieval/optimization/*metrics.csv` | All means recomputed exactly | Not an external or truly unseen-source test |
| Confirmation text and words+characters Hit@10 4.733 %; MRR@50 difference −0.000130 with CI including zero | Confirmation per-query scores | Paired asset-cluster bootstrap | `optimization/paired_differences.csv` | Exactly recomputed | No confirmed optimization gain; not comparable to 06 as an improvement |
| Identity strata; 319/47562 matching valid IDs, 45672 discordant cases | Cleaned records and asset mentions | `tools.prepare_independent_review.py`; identifier concordance audit | `independent_review/identity_audit.csv`, `identity_summary.csv`, `optimization/target_audit.json` | Stratum aggregation recomputed | Disagreement does not establish which field is correct |
| 81 identity-review records, 40 queries, 810 blinded pairs | Fixed review selection and pooled top 10 | `tools.prepare_independent_review.py`; notebook 08 | `independent_review/protocol.json`, `blinded_pairs.csv`, ranking key | Saved counts available; previous repetition verified | Human annotation pending; query graph/candidate feature asymmetry |
| 54 original artifacts, 9 optimization artifacts, 6 review artifacts identical on historical repeats | Earlier execution hashes | Runner/extension repetition | `docs/*reproducibility.json` | Historical records retained | Not a fresh complete double execution in this audit |
| New graph schema checks, provenance categories and structural diagnostics | Actual nodes/edges and explicit schema | `src.graph_quality`; `tools/research_audit.py` | `results/graph_quality_report.json/csv`, provenance summary | Regenerated, repeated deterministically | Passing checks does not validate extraction semantics |
| New candidate-window membership and PRECEDES sidecar | Original events/windows and sorted sensor timestamps | `src.temporal_lineage` | `results/temporal/*` | Regenerated and independently contract-tested | Additive output, no alteration to original graph counts |

The machine-readable verification result is `results/result_verification.json`. The 77-file pre-change hash baseline records which historical values were protected. A future result without a source/computation/artifact chain must be flagged rather than filled in.

## Detailed results and interpretation

The figures below come from saved results, not estimates of future performance. Descriptive hypotheses are formulated here from experiments already conducted: they are not preregistered hypotheses. Each conclusion retains the scope of its experiment.

### Data, extraction, and integration

- MetroPT-3: 1516948 real observations, 15 channels, and a median interval of 10 seconds. Maintenance: a fixed sample of 50000 synthetic records from an independent source.
- Removing 1150 exact duplicates left 48850 records, 9400 syntactically valid asset identifiers, and 410689 entity mentions. Valid syntax does not certify physical identity.
- Integrated graph: 61278 nodes and 621865 edges, including 48613 work orders and 2934 events. All 7/7 integration checks pass: provenance, evidence, existing endpoints, and no direct identity links between sources. These are structural checks, not human semantic validation.
- Extraction review of 100 records remains pending. Coverage measures entity presence, not extraction precision or recall.


| entity_type | records_with_entity | coverage |
| --- | --- | --- |
| equipment_type | 27207 | 55.695 % |
| failure_mode | 15347 | 31.417 % |
| component | 38449 | 78.708 % |
| maintenance_action | 47709 | 97.664 % |
| asset_mention | 47247 | 96.719 % |

Sources and provenance: [manifest](../results/data_manifest.json), [snapshot](../data/raw/source_snapshot.json), [extraction](../results/text/summary.json), [graph](../results/kg/summary.json), [checks](../results/kg/integration_checks.csv).

### Sensor events

Calibration uses only February 2020 and distinguishes COMP operating regimes. Official failure periods are consulted after event extraction has been fixed.

| Indicator | Result |
| --- | --- |
| Events | 2934 |
| Candidate / eligible windows | 9472 / 41042 |
| Flagged fraction | 23.079 % |
| Failure periods overlapped | 4 of 4 |
| Hours of flagged observed windows | 789.333 |
| Total event-interval duration, including merged gaps | 1110.333 hours |
| Windows with insufficient observations | 13283 |

**Conclusion:** all four periods have temporal coverage, with a high alert burden. No validated false-alarm rate, failure lead time, or diagnostic accuracy was estimated. Unlabelled windows are not assumed healthy. Four periods are insufficient to demonstrate generalization.

[Calibration and summary](../results/sensor/summary.json) · [Overlaps](../results/sensor/failure_overlap.csv).

### Initial category-retrieval diagnostic — notebook 05

12253 records, six categories extracted from the text itself, and up to 1500 queries per split. Explicit failure phrases and failure nodes are removed from features, but labels still come from the extractor: they are not independent ground truth.


| split | method | hit@1 | hit@5 | hit@10 | hit@20 | hit@50 | mrr@10 | mrr@50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Equipment-disjoint | Graph context | 98.733 % | 99.600 % | 99.933 % | 99.933 % | 100.000 % | 0.991543 | 0.991574 |
| Equipment-disjoint | Hybrid RRF | 100.000 % | 100.000 % | 100.000 % | 100.000 % | 100.000 % | 1.000000 | 1.000000 |
| Equipment-disjoint | Prior | 23.333 % | 23.333 % | 23.333 % | 23.333 % | 23.333 % | 0.233333 | 0.233333 |
| Equipment-disjoint | TF-IDF | 100.000 % | 100.000 % | 100.000 % | 100.000 % | 100.000 % | 1.000000 | 1.000000 |
| Random | Graph context | 98.800 % | 99.667 % | 99.800 % | 99.867 % | 99.867 % | 0.991689 | 0.991737 |
| Random | Hybrid RRF | 99.800 % | 100.000 % | 100.000 % | 100.000 % | 100.000 % | 0.998667 | 0.998667 |
| Random | Prior | 25.867 % | 25.867 % | 25.867 % | 25.867 % | 25.867 % | 0.258667 | 0.258667 |
| Random | TF-IDF | 99.933 % | 100.000 % | 100.000 % | 100.000 % | 100.000 % | 0.999667 | 0.999667 |
| Template-disjoint | Graph context | 91.400 % | 99.000 % | 99.000 % | 99.467 % | 100.000 % | 0.933733 | 0.934157 |
| Template-disjoint | Hybrid RRF | 97.600 % | 100.000 % | 100.000 % | 100.000 % | 100.000 % | 0.987889 | 0.987889 |
| Template-disjoint | Prior | 1.800 % | 1.800 % | 1.800 % | 1.800 % | 1.800 % | 0.018000 | 0.018000 |
| Template-disjoint | TF-IDF | 99.933 % | 100.000 % | 100.000 % | 100.000 % | 100.000 % | 0.999667 | 0.999667 |

The random split shares 204 exact texts, 55 templates, and 994 equipment identifiers. The template-disjoint split removes text/template overlap but shares 792 equipment identifiers. The equipment-disjoint split removes equipment overlap but retains 199 exact texts and 52 templates.

**Conclusion:** near-100 % scores are diagnostic results from a synthetic corpus with derived labels and repetitive structure. They do not establish industrial diagnosis or real failure retrieval. This finding motivated the structured target and controls in 06.

[Split audit](../results/retrieval/diagnostic/findings.json) · [Complete metrics](../results/retrieval/diagnostic/metrics.csv).

### Retrieval of records for the same asset — notebook 06

Cohort: 38534 records and 5128 assets; an index of 37034 candidates; 1500 queries from 1246 assets. There are 10 conflicting work orders excluded. Every query has at least one eligible positive; the median is 6 positives among 36799.5 eligible candidates.

Numeric identifiers are masked; the same row, work order, and normalized template are excluded; representations are fitted only on candidates; and the full eligible pool is evaluated. RRF fusion uses complete rankings. All 8/8 programmed checks pass. The graph representation is one-hop entity context, not a reasoning model or GNN. This is known-asset retrieval: assets are present in the index, whereas query records are not.


| method | hit@1 | hit@5 | hit@10 | hit@20 | hit@50 | mrr@10 | mrr@50 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Graph context full | 0.200 % | 1.000 % | 2.267 % | 4.400 % | 7.533 % | 0.006049 | 0.008430 |
| Graph context without failure_mode | 0.133 % | 0.867 % | 2.067 % | 3.933 % | 7.667 % | 0.004923 | 0.007334 |
| Hybrid RRF | 0.133 % | 1.067 % | 3.333 % | 4.800 % | 11.133 % | 0.006875 | 0.009785 |
| Masked TF-IDF | 0.400 % | 1.667 % | 3.333 % | 6.600 % | 13.533 % | 0.010198 | 0.014559 |
| Random expectation | 0.022 % | 0.111 % | 0.221 % | 0.442 % | 1.100 % | 0.000649 | 0.000994 |

Hit@k indicates whether at least one record for the same asset occurs among the top k; MRR@k is the reciprocal rank of the first hit, or zero if absent. These metrics must not be compared with the category diagnostic: the target and protocol differ.

Main findings:

- Text exceeds exact random expectation in Hit@10: lift 15.055839, 95 % CI [11.054839; 19.214707]. Full graph: lift 10.237971, 95 % CI [7.027305; 13.611594]. There is signal relative to these synthetic labels; physical identity and operational usefulness are not established.
- Full graph minus text: Hit@10 −0.010667, 95 % CI [−0.019718; −0.001312]. It does not outperform the text baseline.
- Hybrid minus graph: Hit@10 +0.010667, 95 % CI [0.003987; 0.018018]. Adding text improves this indicator over graph alone.
- Hybrid minus text: MRR@50 −0.004774, 95 % CI [−0.008094; −0.002083]. Fusion worsens ranking relative to text; Hit@10 stays equal.
- Full graph minus graph without failure: Hit@10 +0.002000, 95 % CI [−0.000673; 0.005338], with no confirmed improvement on that indicator. MRR@50 +0.001096, 95 % CI [0.000019; 0.002633]: a positive exploratory indication, with an interval close to zero and multiple unadjusted comparisons.

The 95 % CIs use 500 asset-level resamples, not independent row resampling. No correction for multiple metrics/comparisons or sensitivity analysis across seeds was performed; the intervals do not support universal claims.

[Protocol](../results/retrieval/asset/protocol.json) · [Checks](../results/retrieval/asset/leakage_checks.csv) · [All paired differences and CIs](../results/retrieval/asset/paired_differences.csv) · [All method intervals](../results/retrieval/asset/confidence_intervals.csv) · [All lifts](../results/retrieval/asset/lift.csv).

### Subsequent optimization — notebook 07

There were 1500 new queries removed from the index with seed 314159. The 1500 exposed queries from 06 were used for development. Six predefined configurations were compared; selection used development MRR@50 and was saved before confirmation evaluation. Frequencies and vocabularies are fitted to the index. The sample still comes from the previously audited corpus, with neither external validation nor a real temporal split.

Development:


| method | hit@1 | hit@5 | hit@10 | hit@20 | hit@50 | mrr@10 | mrr@50 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| character | 0.200 % | 2.067 % | 3.933 % | 6.933 % | 15.067 % | 0.010057 | 0.014347 |
| graph_idf | 0.200 % | 1.000 % | 2.333 % | 3.800 % | 7.933 % | 0.006155 | 0.008313 |
| word | 0.467 % | 1.933 % | 3.533 % | 6.867 % | 14.000 % | 0.010579 | 0.014763 |
| word_character | 0.400 % | 1.733 % | 3.600 % | 6.933 % | 14.800 % | 0.010584 | 0.015027 |
| word_character_graph | 0.333 % | 1.667 % | 3.200 % | 6.067 % | 13.400 % | 0.009061 | 0.013159 |
| word_graph | 0.067 % | 1.467 % | 3.133 % | 6.133 % | 12.667 % | 0.007382 | 0.011276 |

`word_character` was selected, with weights 0.5/0.5. Confirmation:


| method | hit@1 | hit@5 | hit@10 | hit@20 | hit@50 | mrr@10 | mrr@50 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Random expectation | 0.022 % | 0.109 % | 0.219 % | 0.437 % | 1.087 % | 0.000641 | 0.000982 |
| word | 0.400 % | 1.867 % | 4.733 % | 7.933 % | 15.600 % | 0.012393 | 0.016967 |
| word_character | 0.333 % | 1.667 % | 4.733 % | 8.200 % | 16.200 % | 0.012117 | 0.016837 |



| left | right | metric | difference | ci95_low | ci95_high |
| --- | --- | --- | --- | --- | --- |
| word_character | word | hit@10 | 0.000000 | -0.003646 | 0.003390 |
| word_character | word | mrr@50 | -0.000130 | -0.001713 | 0.001586 |

**Conclusion:** words+characters does not show a confirmed improvement over words. The CIs for both differences include zero. Hit@10 of 4.733 % is not an optimization gain over the 3.333 % in 06: the queries and indices differ. All configurations were not evaluated on confirmation to retrospectively choose another winner.

[Protocol](../results/retrieval/optimization/protocol.json) · [Locked selection](../results/retrieval/optimization/locked_selection.json).

### Identity audit and technical review — notebook 08


| identity_status | records |
| --- | --- |
| discordant_mentions | 45672 |
| matching_only | 318 |
| matching_with_other_mentions | 1 |
| missing_structured_id | 1288 |
| no_textual_id | 1571 |

Among 47562 records with a valid structured identifier, 319 contain that same code in the text: 0.6707 %. Across the full deduplicated sample, the fraction is 0.6530 %. The denominators are not mixed. Disagreement does not authorize asset reassignment; mentions of other components/equipment, errors, or synthetic transformations may be involved.

The [published generator](https://github.com/jvachier/industrial-maintenance-synthetic-data/blob/main/src/generators/maintenance_generator.py) changes Equipment_ID by iteration and preserves copied descriptions. This is a plausible mechanism for disagreement. The upstream revision of the frozen sample is unknown: this code is not certified to explain every local case, nor is the suffix interpreted as real identity.

A stratified sample of 81 records was prepared for identity review. Technical review uses 40 queries, 20 for development and 20 for confirmation. Only the query problem enters ranking: its known intervention and structured metadata are excluded. Candidates must include an action. Pooling the top 10 of words, characters, and graph IDF yields 810 unique pairs for blinded review.

The first pool had 727 pairs and 353 candidates without interventions. This finding motivated the available-action filter; the earlier figures are not compared with the corrected index as evidence of independent improvement. Human annotations remain pending.

Human relevance and safety review remains pending. The confirmation pool has already been inspected in earlier analysis and is not an untouched external test.

### Hypotheses and evidence status

| Hypothesis or claim | Status | Scope and conclusion |
| --- | --- | --- |
| H1. Text retains signal relative to asset labels after the implemented controls | Supported in this sample | Hit@10 lift above random; does not establish identification of real machines |
| H2. Graph entity context retains signal relative to those labels | Supported in this sample | Above random, but below text |
| H3. Adding text improves graph alone | Supported for Hit@10 in 06 | Positive paired comparison; not an improvement on every indicator |
| H4. Adding graph improves the best text baseline | Not supported | Equal Hit@10 and worse MRR@50 for fusion in 06 |
| H5. Failure entities provide incremental value to the graph | Mixed, exploratory evidence | Hit@10 unconfirmed; slightly positive MRR@50 without multiplicity adjustment |
| H6. Words+characters improves words on new queries | Not confirmed | Confirmation differences compatible with zero |
| H7. Eventization covers known failure periods | Descriptive observation | Overlap 4/4, with 23.079 % of windows flagged; specificity and lead-time validation missing |
| H8. Structured identities systematically agree with textual identities | Not supported | 45672 discordant cases; no automatic certification of the correct field |
| H9. A graph can integrate separate sources with provenance without inventing identity | Structural feasibility demonstrated | 7/7 checks; no predictive usefulness or causality established |
| H10. The system retrieves useful and safe interventions for real maintenance | Pending | Expert review and related real data are missing |
| H11. Graph is more robust than text with incomplete or degraded information | Not evaluated | Subsequent proposal; no experiment or result yet |
| H12. Results generalize to another source, plant, or period | Not evaluated | No external retrieval validation |

Claims of accurate extraction, causal diagnosis, shared identity across datasets, validated early warning, and production readiness are also unproven. Negative and pending results remain part of the study.

### Reproducibility and evidence limitations

- 00–06: two full runs with a clean kernel for each notebook, yielding 54 identical artifacts. This is historical evidence for that version, not certification of two complete runs of the current extended pipeline.
- 07: nine identical artifacts on repetition. 08, after intervention filtering: six identical artifacts. The review page has deterministic generation; browser interaction was not automatically verified.
- All 22 methodological tests pass. They validate code contracts and behavior, not semantic accuracy or industrial usefulness.
- The maintenance sample is synthetic, fixed, and has no known upstream revision. There are no real shared identifiers between sensors and text or an independent corpus of adjudicated relevance.
- Additional hypotheses are described after the results, without claiming nonexistent preregistration.

[Original verification](reproducibility.json) · [Optimization](optimization_reproducibility.json) · [Review](independent_review_reproducibility.json) · [Page](review_app_verification.json).

### Conclusion and publication scope

The defensible outcome is a reproducible prototype and an exploratory study of identity auditing, evaluation shortcuts, and representation comparison in synthetic maintenance, alongside eventization of a real sensor source. Neither graph improvement over the text baseline nor industrial usefulness of retrieved interventions has been demonstrated.

Scopus is an index covering journals and conference proceedings; proceedings and Scopus are not mutually exclusive alternatives. Acceptance is decided by the venue and manuscript review, not by the index. [Official Scopus coverage](https://www.elsevier.com/products/scopus/content?trial=true).

A conservative assessment of the current state, without predicting acceptance:

| Publication target | Assessment |
| --- | --- |
| Workshop or short paper at an applied conference | A plausible initial target with a clearly delimited methodological contribution and a solid manuscript; rejection for insufficient novelty or validation remains possible |
| Full paper at a selective conference | Current evidence and contribution are insufficient to consider it ready |
| Scopus-indexed journal, including Q3/Q4 | Not considered ready; no quartile can be assigned to the project and acceptance in less-cited journals cannot be guaranteed |
| Competitive Q1/Q2 journal | Not a defensible immediate target with this evidence |

Quartiles depend on the journal, category, year, and ranking system; they do not directly rate a repository. This assessment is a judgement of research maturity, not external peer review. A negative result can contribute if it offers a novel explanation, solid controls, and a generalizable lesson; reproducibility alone does not establish novelty.

To advance: assess literature and novelty, obtain adjudicated relevance or an independent source, test robustness across seeds, define primary metrics and multiplicity before new experiments, and validate a specific hypothesis under a reserved protocol. [IEEE conference review](https://conferences.ieeeauthorcenter.ieee.org/understand-peer-review/) considers, among other factors, whether there is a significant contribution; [IEEE Access reviewer guidance](https://ieeeaccess.ieee.org/reviewers/reviewer-best-practices/) also requires sufficient benchmarking and validation and conclusions supported by evidence.

No new external datasets have been incorporated into these results. Suggested external sources are options for future studies, not evidence already obtained.
