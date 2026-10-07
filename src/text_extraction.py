import re

import pandas as pd

from .data import MISSING_IDS, NON_ASSET_PREFIXES, validate_equipment_id

ASSET_PATTERN = re.compile(r"(?<![\w-])[A-Z]{1,6}-\d{1,4}[A-Z]?(?![\w-])")


def clean_text(value):
    if pd.isna(value):
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return "" if text.upper() in MISSING_IDS else text


def extract_asset_mentions(text):
    return [(m.group(), m.start(), m.end()) for m in ASSET_PATTERN.finditer(text)
            if m.group().split("-")[0] not in NON_ASSET_PREFIXES]


def extract_entities(text, kind):
    candidates = []
    for label, pattern in COMPILED[kind].items():
        candidates.extend((label, m.group(), m.start(), m.end()) for m in pattern.finditer(text))
    candidates.sort(key=lambda x: (-(x[3] - x[2]), x[2], x[0]))
    selected = []
    for hit in candidates:
        if not any(hit[2] < other[3] and hit[3] > other[2] for other in selected):
            selected.append(hit)
    return sorted(selected, key=lambda x: (x[2], x[0]))


def extract_records(frame):
    records, entities = [], []
    for row in frame.itertuples(index=False):
        problem = clean_text(row.WorkOrderDescription)
        action = clean_text(row.OperationDescription)
        work_order = clean_text(row.WorkOrder) or f"ROW_{row.row_id:06d}"
        record = dict(row_id=int(row.row_id), work_order=work_order,
                      equipment_id=validate_equipment_id(row.Equipment_ID),
                      equipment_id_raw=clean_text(row.Equipment_ID),
                      order_type=clean_text(row.OrderType).upper(),
                      maintenance_type=clean_text(row.Maintenance_activity_type).upper(),
                      problem_text=problem, action_text=action,
                      combined_text=clean_text(problem + " " + action))
        for kind in COMPILED:
            fields = [("WorkOrderDescription", problem), ("OperationDescription", action)]
            if kind in {"equipment_type", "failure_mode"}:
                fields = fields[:1]
            if kind == "maintenance_action":
                fields = fields[1:]
            hits = []
            for field, text in fields:
                for label, evidence, start, end in extract_entities(text, kind):
                    hits.append(label)
                    entities.append(dict(row_id=int(row.row_id), work_order=work_order,
                                         entity_type=kind, entity_label=label, source_field=field,
                                         evidence=evidence, span_start=start, span_end=end))
            record[f"n_{kind}"] = len(set(hits))
        asset_labels = []
        for field, text in [("WorkOrderDescription", problem), ("OperationDescription", action)]:
            for label, start, end in extract_asset_mentions(text):
                asset_labels.append(label)
                entities.append(dict(row_id=int(row.row_id), work_order=work_order,
                                     entity_type="asset_mention", entity_label=label, source_field=field,
                                     evidence=label, span_start=start, span_end=end))
        record["n_asset_mention"] = len(set(asset_labels))
        record["identifier_concordance"] = bool(record["equipment_id"]) and record["equipment_id"] in asset_labels
        records.append(record)
    columns = ["row_id", "work_order", "entity_type", "entity_label", "source_field", "evidence", "span_start", "span_end"]
    return pd.DataFrame(entities, columns=columns), pd.DataFrame(records)

LEXICONS = {'equipment_type': {'centrifugal_pump': '\\bcentrifugal\\s+pumps?\\b',
                    'screw_conveyor': '\\bscrew\\s+conveyors?\\b',
                    'air_compressor': '\\bair\\s+compressors?\\b',
                    'electric_motor': '\\belectric\\s+motors?\\b',
                    'gearbox': '\\bgear(?:\\s*box(?:es)?|boxes?)\\b',
                    'pump': '\\bpumps?\\b',
                    'motor': '\\bmotors?\\b',
                    'compressor': '\\bcompressors?\\b',
                    'conveyor': '\\bconveyors?\\b',
                    'fan': '\\bfans?\\b',
                    'valve': '\\bvalves?\\b'},
 'failure_mode': {'earth_fault': '\\bearth\\s+fault\\b',
                  'electrical_fault': '\\belectrical\\s+fault\\b|\\bshort\\s+circuit\\b',
                  'high_vibration': '\\bhigh\\s+vibration\\b|\\bexcessive\\s+vibration\\b|\\bvibration\\s+alarm\\b',
                  'air_leak': '\\bair\\s+leak(?:age)?\\b',
                  'leak': '\\bleak(?:age|ing)?\\b',
                  'overheating': '\\boverheat(?:ing|ed)?\\b|\\bhigh\\s+temperature\\b',
                  'bearing_failure': '\\bbearing\\s+(?:failure|fault|damage)\\b',
                  'pressure_loss': '\\bpressure\\s+(?:drop|loss)\\b|\\blow\\s+pressure\\b',
                  'misalignment': '\\bmisalign(?:ment|ed)?\\b',
                  'blockage': '\\bblock(?:age|ed)?\\b|\\bclogg(?:ed|ing)?\\b|\\bobstruction\\b',
                  'corrosion': '\\b(?:corrosion|corrosive|corroded|corroding)\\b',
                  'crack': '\\bcrack(?:ed|ing|s)?\\b|\\bfracture\\b',
                  'wear': '\\bwear\\b|\\bworn\\b',
                  'trip': '\\btrip(?:ped|ping)?\\b'},
 'component': {'bearing': '\\bbearings?\\b',
               'seal': '\\bseals?\\b',
               'shaft': '\\bshafts?\\b',
               'coupling': '\\bcouplings?\\b',
               'gearbox': '\\bgear(?:\\s*box(?:es)?|boxes?)\\b',
               'motor': '\\bmotors?\\b',
               'pump': '\\bpumps?\\b',
               'valve': '\\bvalves?\\b',
               'filter': '\\bfilters?\\b',
               'belt': '\\bbelts?\\b',
               'hose': '\\bhoses?\\b',
               'pipe': '\\bpipes?\\b|\\bpiping\\b',
               'compressor': '\\bcompressors?\\b',
               'conveyor': '\\bconveyors?\\b',
               'fan': '\\bfans?\\b',
               'sensor': '\\bsensors?\\b',
               'cylinder': '\\bcylinders?\\b',
               'liner': '\\bliners?\\b',
               'impeller': '\\bimpellers?\\b'},
 'maintenance_action': {'inspect': '\\binspect(?:s|ion|ed|ing)?\\b',
                        'replace': '\\breplac(?:e|ed|ement|ing)\\b',
                        'repair': '\\brepair(?:ed|ing)?\\b',
                        'lubricate': '\\blubricat(?:e|ed|ion|ing)\\b|\\bgreas(?:e|ed|ing)\\b',
                        'clean': '\\bclean(?:ed|ing)?\\b',
                        'tighten': '\\btighten(?:ed|ing)?\\b',
                        'align': '\\balign(?:ed|ment|ing)?\\b',
                        'test': '\\btest(?:ed|ing)?\\b|\\bcheck(?:ed|ing)?\\b',
                        'isolate': '\\bisolat(?:e|ed|ion|ing)\\b',
                        'monitor': '\\bmonitor(?:ed|ing)?\\b',
                        'calibrate': '\\bcalibrat(?:e|ed|ion|ing)\\b',
                        'adjust': '\\badjust(?:ed|ment|ing)?\\b',
                        'reset': '\\breset(?:ting)?\\b',
                        'install': '\\binstall(?:ed|ing|ation)?\\b'}}

COMPILED = {kind: {label: re.compile(pattern, re.I) for label, pattern in entries.items()}
            for kind, entries in LEXICONS.items()}
