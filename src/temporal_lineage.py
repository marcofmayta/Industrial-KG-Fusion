
import numpy as np
import pandas as pd


def temporal_lineage(events, windows, observations=None, frequency='5min'):
    events = events.copy()
    events['start'] = pd.to_datetime(events.start, errors='raise')
    events['end'] = pd.to_datetime(events.end, errors='raise')
    if events.event_id.duplicated().any() or events[['start', 'end']].isna().any().any() or events.end.le(events.start).any():
        raise ValueError('Events require unique IDs and valid positive intervals.')
    events = events.sort_values(['start', 'event_id']).reset_index(drop=True)
    if len(events) > 1 and (events.start.iloc[1:].to_numpy() < events.end.iloc[: -1].to_numpy()).any():
        raise ValueError('Merged event intervals must not overlap.')
    windows = windows.copy()
    windows['timestamp'] = pd.to_datetime(windows.timestamp, errors='raise')
    if windows.timestamp.isna().any() or windows.timestamp.duplicated().any():
        raise ValueError('Windows require unique valid timestamps.')
    candidate = windows.loc[windows.candidate].sort_values('timestamp').reset_index(drop=True)
    rows = []
    delta = pd.Timedelta(frequency)
    for row in events.itertuples(index=False):
        selected = candidate.loc[candidate.timestamp.ge(row.start) & candidate.timestamp.lt(row.end)]
        if len(selected) != row.n_windows or (selected.timestamp+delta).gt(row.end).any():
            raise ValueError('Event candidate-window membership disagrees with extracted events.')
        for window in selected.itertuples(index=False):
            rows.append(dict(event_id=row.event_id, window_start=window.timestamp, window_end=window.timestamp+delta,
                n_valid_observations=int(window.n_obs), score=float(window.score), source_dataset='metropt3',
                source_artifact='results/sensor/window_scores.parquet', relation_origin='deterministic_window_membership'))
    membership = pd.DataFrame(rows, columns=['event_id', 'window_start', 'window_end', 'n_valid_observations', 'score', 'source_dataset', 'source_artifact', 'relation_origin'])
    if len(membership) != len(candidate) or membership.window_start.duplicated().any():
        raise ValueError('Every candidate window must map to exactly one event.')
    if observations is not None:
        obs = pd.DatetimeIndex(observations)
        if obs.hasnans or not obs.is_monotonic_increasing:
            raise ValueError('Observation timestamps must be sorted and nonmissing.')
        membership['observation_row_start'] = np.searchsorted(obs, membership.window_start, side='left')
        membership['observation_row_end_exclusive'] = np.searchsorted(obs, membership.window_end, side='left')
        if (membership.observation_row_end_exclusive-membership.observation_row_start < membership.n_valid_observations).any():
            raise ValueError('Valid observation count exceeds available source rows.')
    adjacency = []
    for previous, current in zip(events.iloc[: -1].itertuples(), events.iloc[1:].itertuples()):
        adjacency.append(dict(source='sensor_event:'+previous.event_id, relation='PRECEDES', target='sensor_event:'+current.event_id,
            gap_minutes=(current.start-previous.end).total_seconds()/60, source_dataset='metropt3',
            source_artifact='results/sensor/events.csv', relation_origin='deterministic_chronological_adjacency',
            semantics='Immediate adjacency of nonoverlapping source-local intervals; not causality'))
    return membership, pd.DataFrame(adjacency, columns=['source', 'relation', 'target', 'gap_minutes', 'source_dataset', 'source_artifact', 'relation_origin', 'semantics'])
