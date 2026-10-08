# Implemented architecture

```mermaid
flowchart TD
    M[Public synthetic maintenance snapshot] --> V[Schema and identity audit<br/>exact duplicate removal]
    V --> T[Clean text and extract lexical entities<br/>retain spans and row evidence]
    T --> W[Maintenance property-graph branch]
    S[Public MetroPT sensor time series] --> B[February reference calibration<br/>COMP-specific robust statistics]
    B --> E[Score observations and five-minute windows<br/>merge candidate windows into intervals]
    E --> G[Sensor property-graph branch]
    W --> O[Manual concept and class bridge<br/>no physical identity join]
    G --> O
    O --> Q[Schema, provenance and graph-quality audit]
    E --> L[Window and observation lineage<br/>chronological adjacency sidecar]
    W --> R[Candidate-fitted text and entity-context retrieval]
    R --> D[Diagnostic category experiment<br/>text-derived labels]
    D --> C[Stricter known-asset experiment<br/>identifier and template controls]
    C --> U[Asset-cluster bootstrap<br/>paired differences and ablation]
    U --> P[Subsequent development and confirmation<br/>optimization not confirmed]
    P --> H[Problem-only review pool<br/>human labels pending]
    Q --> F[Saved-artifact traceability and result preservation]
    L --> F
    U --> F
```

This diagram describes current computations, not a proposed trained multimodal model. Retrieval uses the maintenance branch; the sensor branch contributes event modeling and conceptual navigation, but has no validated relevance link to maintenance candidates. Graph learning is a prospective research question rather than an implemented result.

Core implementations live under `src/`; notebooks retain experiment-specific protocol, cohort selection and analysis. `tools/run_pipeline.py` executes clean notebook kernels, preserves previous results before replacing them, and produces additive quality/temporal audits. `tools/research_audit.py` verifies saved numerical artifacts without rerunning expensive rankings.
