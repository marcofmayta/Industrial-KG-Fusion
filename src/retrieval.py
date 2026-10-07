import re
from urllib.parse import unquote

import numpy as np
import pandas as pd
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from .config import SEED
from .knowledge_graph import RELATIONS

IDENTIFIER_TOKEN = re.compile(r"\b(?=[a-z0-9_./-]*\d)[a-z0-9]+(?:[-_/\.][a-z0-9]+)*\b")


def mask_identifiers(text):
    text = IDENTIFIER_TOKEN.sub(" identifier ", str(text).lower())
    text = re.sub(r"\d+", " identifier ", text)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", text)).strip()


def normalize_template(text):
    return re.sub(r"\s+", " ", mask_identifiers(text)).strip()


def build_graph_features(records, edges, include_failure=True, include_structured=True):
    allowed = {"equipment_type", "component", "maintenance_action"}
    if include_failure:
        allowed.add("failure_mode")
    relations = {RELATIONS[kind]: kind for kind in allowed}
    if include_structured:
        relations.update(HAS_ORDER_TYPE="order_type", HAS_MAINTENANCE_TYPE="maintenance_type")
    features = edges.loc[edges["source_dataset"].eq("maintenance") & edges["relation"].isin(relations)].copy()
    features["row_id"] = pd.to_numeric(features["row_id"], errors="raise")
    if features["row_id"].isna().any():
        raise ValueError("Feature edges require row-level provenance.")
    features["token"] = features["relation"].map(relations) + ":" + features["target"].str.split(":", n=1).str[1].map(unquote)
    by_row = features.groupby("row_id")["token"].agg(lambda x: sorted(set(x))).to_dict()
    output = []
    for row in records.itertuples(index=False):
        tokens = by_row.get(row.row_id, []).copy()
        output.append({token: 1.0 for token in sorted(set(tokens))})
    return output


def fit_representations(candidates, queries, candidate_graph, query_graph):
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=.98,
                               max_features=30000, sublinear_tf=True)
    text_candidates = normalize(vectorizer.fit_transform(candidates))
    text_queries = normalize(vectorizer.transform(queries))
    graph_vectorizer = DictVectorizer(sparse=True, sort=True)
    graph_candidates = normalize(graph_vectorizer.fit_transform(candidate_graph))
    graph_queries = normalize(graph_vectorizer.transform(query_graph))
    return text_candidates, text_queries, graph_candidates, graph_queries


def reciprocal_rank_fusion(rankings, k=60):
    if not rankings:
        return np.array([], dtype=int)
    pool = rankings[0]
    if any(set(r) != set(pool) for r in rankings):
        raise ValueError("RRF requires the same complete candidate pool for all methods.")
    scores = np.zeros(max(pool, default=-1) + 1)
    for ranking in rankings:
        scores[ranking] += 1 / (k + np.arange(1, len(ranking) + 1))
    # The first ranking already uses a label-independent tie order.
    return pool[np.argsort(-scores[pool], kind="stable")]


def rank_candidates(candidate_matrices, query_matrices, candidates, queries, exclude_templates=False):
    if len(candidate_matrices) != len(query_matrices):
        raise ValueError("Candidate/query representations do not align.")
    order = np.random.default_rng(SEED).permutation(len(candidates))
    candidate_rows = candidates["row_id"].to_numpy()
    candidate_orders = candidates["work_order"].to_numpy()
    templates = candidates["template"].to_numpy()
    rankings = [[] for _ in candidate_matrices]
    hybrids, audit = [], []
    # Blocks bound memory without limiting the candidate pool.
    for start in range(0, len(queries), 32):
        stop = min(start + 32, len(queries))
        scores = [(q[start:stop] @ c.T).toarray() for c, q in zip(candidate_matrices, query_matrices)]
        for offset, query in enumerate(queries.iloc[start:stop].itertuples(index=False)):
            eligible = (candidate_rows != query.row_id) & (candidate_orders != query.work_order)
            if exclude_templates:
                eligible &= templates != query.template
            pool = order[eligible[order]]
            current = []
            for method, matrix in enumerate(scores):
                ranking = pool[np.argsort(-matrix[offset, pool], kind="stable")]
                current.append(ranking)
                rankings[method].append(ranking[:50])
            # Fuse complete eligible rankings, then retain the evaluated top 50.
            hybrids.append(reciprocal_rank_fusion([current[0], current[-1]])[:50])
            audit.append(dict(query_id=int(query.row_id), n_candidates=len(pool),
                              self_matches=int((candidate_rows[pool] == query.row_id).sum()),
                              same_work_order_matches=int((candidate_orders[pool] == query.work_order).sum()),
                              same_template_matches=int((templates[pool] == query.template).sum())))
    return rankings, hybrids, pd.DataFrame(audit)
