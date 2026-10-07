import numpy as np
import pandas as pd

from .config import ANALOG, SENSOR_QUANTILE, WINDOW_FREQ, WINDOW_SCORE_QUANTILE, MERGE_GAP_MINUTES


def fit_robust_baseline(baseline, sensors=ANALOG, quantile=SENSOR_QUANTILE):
    if baseline.empty or baseline["COMP"].isna().any():
        raise ValueError("Baseline must contain observations and known COMP regimes.")
    rows = []
    for regime, group in baseline.groupby("COMP", sort=True):
        for sensor in sensors:
            values = group[sensor].dropna().astype(float)
            if len(values) < 2:
                raise ValueError(f"Insufficient calibration for {sensor}, COMP={regime}.")
            median = float(values.median())
            mad = float((values - median).abs().median())
            iqr = float(values.quantile(.75) - values.quantile(.25))
            std = float(values.std())
            scale, method = next(((s, name) for s, name in
                                  [(1.4826 * mad, "MAD"), (iqr / 1.349, "IQR"), (std, "std")]
                                  if np.isfinite(s) and s > 0), (0.0, "constant"))
            threshold = float(((values - median).abs() / scale).quantile(quantile)) if scale else 0.0
            rows.append(dict(COMP=float(regime), sensor=sensor, n=len(values), median=median,
                             mad=mad, iqr=iqr, std=std, scale=scale, scale_method=method,
                             abs_z_threshold=threshold, quantile=quantile))
    return pd.DataFrame(rows)


def score_sensor_points(frame, stats, sensors=ANALOG):
    unknown = set(frame["COMP"].dropna()) - set(stats["COMP"])
    if unknown or frame["COMP"].isna().any():
        raise ValueError(f"Uncalibrated operating regime: {unknown}")
    normalized = pd.DataFrame(index=frame.index, columns=sensors, dtype=float)
    for row in stats.itertuples(index=False):
        mask = frame["COMP"].eq(row.COMP)
        deviation = (frame.loc[mask, row.sensor] - row.median).abs()
        denominator = row.scale * row.abs_z_threshold
        if denominator > 0:
            score = deviation / denominator
        else:
            score = 2 * deviation.gt(0).astype(float)
            score[deviation.isna()] = np.nan
        normalized.loc[mask, row.sensor] = score
    points = pd.DataFrame({"timestamp": frame["timestamp"],
                           "score": normalized.max(axis=1),
                           "n_extreme_channels": normalized.gt(1).sum(axis=1)})
    points["valid"] = normalized.notna().all(axis=1)
    points.loc[~points["valid"], "score"] = np.nan
    return points, normalized


def aggregate_windows(points, normalized, freq=WINDOW_FREQ):
    indexed = points.set_index("timestamp")
    grouped = indexed.resample(freq)
    windows = pd.DataFrame({"n_obs": grouped["score"].count(),
                            "score": grouped["score"].quantile(WINDOW_SCORE_QUANTILE),
                            "score_max": grouped["score"].max(),
                            "extreme_fraction": indexed["n_extreme_channels"].gt(0).resample(freq).mean()})
    values = normalized.copy()
    values.index = pd.DatetimeIndex(points["timestamp"])
    maxima = values.resample(freq).max().add_suffix("_max")
    return windows.join(maxima)


def merge_event_windows(windows, freq=WINDOW_FREQ, gap_minutes=MERGE_GAP_MINUTES):
    candidates = windows.loc[windows["candidate"]]
    columns = ["event_id", "start", "end", "duration_min", "n_windows", "score_max",
               "peak_sensor", "peak_sensor_score", "active_sensors"]
    rows = []
    # Gap is measured between the previous window end and the next window start.
    groups = candidates.index.to_series().diff().gt(pd.Timedelta(freq) + pd.Timedelta(minutes=gap_minutes)).cumsum()
    for number, (_, group) in enumerate(candidates.groupby(groups), start=1):
        maxima = group[[f"{s}_max" for s in ANALOG]].max()
        peak = maxima.idxmax().removesuffix("_max")
        start, end = group.index.min(), group.index.max() + pd.Timedelta(freq)
        rows.append(dict(event_id=f"SE_{number:05d}", start=start, end=end,
                         duration_min=(end - start).total_seconds() / 60, n_windows=len(group),
                         score_max=float(group["score"].max()), peak_sensor=peak,
                         peak_sensor_score=float(maxima[f"{peak}_max"]),
                         active_sensors="|".join(s for s in ANALOG if maxima[f"{s}_max"] > 1)))
    return pd.DataFrame(rows, columns=columns)
