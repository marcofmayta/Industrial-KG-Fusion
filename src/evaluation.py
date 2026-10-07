import numpy as np
import pandas as pd

from .config import BOOTSTRAPS, SEED, TOP_K


def expected_random_hit_probability(n_candidates, positives, k):
    if not 0 <= positives <= n_candidates or k < 0:
        raise ValueError("Invalid candidate/positive counts or k.")
    no_hit = 1.0
    for i in range(min(k, n_candidates)):
        no_hit *= max(n_candidates - positives - i, 0) / (n_candidates - i)
    return float(1 - no_hit)


def expected_random_mrr(n_candidates, positives, k):
    if not 0 <= positives <= n_candidates or k < 0:
        raise ValueError("Invalid candidate/positive counts or k.")
    no_hit, expectation = 1.0, 0.0
    for i in range(min(k, n_candidates)):
        expectation += no_hit * positives / (n_candidates - i) / (i + 1)
        no_hit *= max(n_candidates - positives - i, 0) / (n_candidates - i)
    return float(expectation)


def evaluate_rankings(rankings, queries, candidates, target, method, ks=TOP_K):
    if len(rankings) != len(queries):
        raise ValueError("One ranking is required per query.")
    labels = candidates[target].to_numpy()
    rows = []
    for query, ranking in zip(queries.itertuples(index=False), rankings):
        if len(set(ranking)) != len(ranking):
            raise ValueError("Ranking contains duplicate candidates.")
        relevant = labels[ranking] == getattr(query, target)
        positions = np.flatnonzero(relevant)
        row = dict(method=method, query_id=int(query.row_id), equipment_id=query.equipment_id)
        row.update({f"hit@{k}": float(relevant[:k].any()) for k in ks})
        for k in (10, 50):
            row[f"mrr@{k}"] = float(1 / (positions[0] + 1)) if len(positions) and positions[0] < k else 0.0
        rows.append(row)
    return pd.DataFrame(rows)


def random_expectation(queries, candidates, target="equipment_id", exclude_templates=True):
    rows = []
    for query in queries.itertuples(index=False):
        eligible = candidates["row_id"].ne(query.row_id) & candidates["work_order"].ne(query.work_order)
        if exclude_templates:
            eligible &= candidates["template"].ne(query.template)
        n = int(eligible.sum())
        positives = int((eligible & candidates[target].eq(getattr(query, target))).sum())
        row = dict(method="Random expectation", query_id=int(query.row_id), equipment_id=query.equipment_id,
                   n_candidates=n, positives=positives)
        row.update({f"hit@{k}": expected_random_hit_probability(n, positives, k) for k in TOP_K})
        row.update({f"mrr@{k}": expected_random_mrr(n, positives, k) for k in (10, 50)})
        rows.append(row)
    return pd.DataFrame(rows)


def cluster_bootstrap(values, clusters, repetitions=BOOTSTRAPS, seed=SEED):
    frame = pd.DataFrame({"value": values, "cluster": clusters})
    if frame.empty or frame["cluster"].isna().any():
        raise ValueError("Bootstrap requires observations and known clusters.")
    totals = frame.groupby("cluster", sort=True)["value"].agg(["sum", "count"])
    rng = np.random.default_rng(seed)
    output = []
    sums, counts = totals["sum"].to_numpy(), totals["count"].to_numpy()
    for _ in range(repetitions):
        sample = rng.integers(0, len(totals), size=len(totals))
        output.append(sums[sample].sum() / counts[sample].sum())
    return np.asarray(output)


def bootstrap_ci(results, metrics, cluster="equipment_id"):
    rows = []
    for method, group in results.groupby("method", sort=True):
        for metric in metrics:
            samples = cluster_bootstrap(group[metric].to_numpy(), group[cluster].to_numpy())
            low, high = np.quantile(samples, [.025, .975])
            rows.append(dict(method=method, metric=metric, estimate=float(group[metric].mean()),
                             ci95_low=float(low), ci95_high=float(high), clusters=group[cluster].nunique(),
                             resampling_unit=cluster))
    return pd.DataFrame(rows)


def paired_comparisons(results, metrics, pairs):
    rows = []
    for left, right in pairs:
        a = results.loc[results["method"].eq(left)].set_index("query_id").sort_index()
        b = results.loc[results["method"].eq(right)].set_index("query_id").sort_index()
        if not a.index.equals(b.index):
            raise ValueError("Paired comparisons require identical queries.")
        for metric in metrics:
            difference = a[metric] - b[metric]
            boot = cluster_bootstrap(difference.to_numpy(), a["equipment_id"].to_numpy())
            low, high = np.quantile(boot, [.025, .975])
            rows.append(dict(left=left, right=right, metric=metric, difference=float(difference.mean()),
                             ci95_low=float(low), ci95_high=float(high)))
    return pd.DataFrame(rows)


def lift_intervals(results, metrics):
    random = results.loc[results["method"].eq("Random expectation")].set_index("query_id").sort_index()
    rows = []
    for method, group in results.loc[results["method"].ne("Random expectation")].groupby("method"):
        group = group.set_index("query_id").sort_index()
        if not group.index.equals(random.index):
            raise ValueError("Lift requires matched random expectations.")
        for metric in metrics:
            denominator = random[metric].mean()
            if denominator <= 0:
                raise ValueError("Random expectation is zero; lift is undefined.")
            numerator_boot = cluster_bootstrap(group[metric].to_numpy(), group["equipment_id"].to_numpy())
            denominator_boot = cluster_bootstrap(random[metric].to_numpy(), random["equipment_id"].to_numpy())
            ratios = numerator_boot / denominator_boot
            low, high = np.quantile(ratios, [.025, .975])
            rows.append(dict(method=method, metric=metric, lift=float(group[metric].mean() / denominator),
                             ci95_low=float(low), ci95_high=float(high)))
    return pd.DataFrame(rows)
